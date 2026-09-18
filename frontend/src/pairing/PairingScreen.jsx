import React,{useEffect,useRef,useState} from "react";
import QRCode from "qrcode";
import {base64UrlDecode,base64UrlEncode,createX25519KeyPair,deriveSessionKey,deriveX25519SharedSecret,getBrowserIdentity,makeClientPairingConfirmation,verifyServerPairingConfirmation} from "../security/crypto";

const localLoopback = ["localhost", "127.0.0.1", "::1"].includes(location.hostname) || /^127\./.test(location.hostname);
const serviceOrigin = import.meta.env.VITE_SERVICE_URL || (localLoopback ? "http://127.0.0.1:8443" : `https://${location.hostname}:8443`);
const publicFrontendOrigin = import.meta.env.VITE_PUBLIC_FRONTEND_ORIGIN || location.origin;

function DeviceIdentity({title,identity={},fingerprint}){return <section className="pairing-identity" aria-label={`${title} identity`}><h2>{title}</h2><dl><div><dt>Device</dt><dd>{identity.hostname||identity.device_name||identity.label||"Not reported"}</dd></div><div><dt>Model</dt><dd>{identity.model||"Not reported"}</dd></div><div><dt>User</dt><dd>{identity.user||"Not reported"}</dd></div><div><dt>IP address</dt><dd>{identity.ip||"Not reported"}</dd></div><div><dt>MAC address</dt><dd>{identity.mac||"Not exposed by browser"}</dd></div><div><dt>Identity key</dt><dd>{fingerprint||"Verified during encrypted handshake"}</dd></div></dl></section>}

function StartupScreen(){return <main className="startup-screen">
    <div className="startup-circuit" aria-hidden="true"/>
    <header className="startup-topbar"><strong>TRACEPULSE</strong><span>DESKTOP AGENT&nbsp; / &nbsp;v1.0.0</span></header>
    <section className="startup-main" aria-label="TracePulse is starting">
        <div className="startup-radar" aria-hidden="true"><i className="startup-ring startup-ring-outer"/><i className="startup-ring startup-ring-middle"/><i className="startup-ring startup-ring-inner"/><svg viewBox="0 0 32 32" role="img" aria-label="Security shield"><path d="M16 3 26 7v7c0 6.6-4.1 12-10 15-5.9-3-10-8.4-10-15V7l10-4Z"/><path d="m11 16 3.2 3.2L21.5 12"/></svg></div>
        <h1>TRACEPULSE</h1><strong className="startup-tagline">YOUR DEVICE. OUR PROTECTION.</strong>
        <p>Intelligent proximity. Uncompromising security.</p>
        <div className="startup-progress" aria-label="Initializing security modules"><span>INITIALIZING SECURITY MODULES…</span><div><i/></div></div>
    </section>
</main>;}

export default function PairingScreen({onPaired,phoneMode=false}){
    useEffect(()=>{if(phoneMode)localStorage.setItem("tracepulse.role","phone");else localStorage.setItem("tracepulse.role","laptop");},[phoneMode]);
    const scanned=location.hash.includes("pairing_handle");
    const [showStart,setShowStart]=useState(scanned);
    const [payload,setPayload]=useState(scanned?location.href:"");
    const [qr,setQr]=useState("");
    const [error,setError]=useState("");
    const [busy,setBusy]=useState(false);
    const [phoneConfirmed,setPhoneConfirmed]=useState(false);
    const [laptopPending,setLaptopPending]=useState(false);
    const [pendingSession,setPendingSession]=useState(null);
    const [pairingReview,setPairingReview]=useState(null);
    const [pendingIdentity,setPendingIdentity]=useState(null);
    const [laptopIdentity,setLaptopIdentity]=useState(null);
    const [serverKeyFingerprint,setServerKeyFingerprint]=useState("");
    const [log,setLog]=useState(["System initialized","Security protocols engaged","Awaiting phone connection..."]);
    const offerStarted=useRef(false);

    useEffect(()=>{
        if(scanned||showStart)return;
        const timer=setTimeout(()=>setShowStart(true),5000);
        return()=>clearTimeout(timer);
    },[scanned,showStart]);

    useEffect(()=>{
        if(phoneMode||payload||!showStart)return;
        if(offerStarted.current)return;
        offerStarted.current=true;
        let cancelled=false;
        fetch(`${serviceOrigin}/api/pairing/prepare`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})
            .then(response=>{if(!response.ok)throw Error("pairing offer unavailable");return response.json();})
            .then(offer=>{
                setLaptopIdentity(offer.laptop);setServerKeyFingerprint(offer.server_key_fingerprint);
                const source=new URL(offer.qr_payload);
                const params=new URLSearchParams(source.hash.slice(1));
                params.set("service_origin",serviceOrigin);
                params.set("server_key_fingerprint",offer.server_key_fingerprint);
                const pairingUrl=`${publicFrontendOrigin}${location.pathname}?role=phone#${params}`;
                return Promise.all([pairingUrl,QRCode.toDataURL(pairingUrl,{margin:2,width:300})]);
            })
            .then(([value,image])=>{if(!cancelled){setPayload(value);setQr(image);setLog(items=>[...items,"Secure pairing QR generated"]);}})
            .catch(exception=>{if(!cancelled)setError(exception.message||"pairing offer unavailable");});
        return ()=>{cancelled=true;};
    },[payload,showStart,phoneMode]);

    useEffect(()=>{
        if(scanned)return;
        let stopped=false;
        const check=async()=>{
            try{
                const response=await fetch(`${serviceOrigin}/api/status`,{cache:"no-store"});
                if(!response.ok)return;
                const status=await response.json();
                if(!stopped&&status.session?.active&&!status.session?.approved){setLaptopPending(true);setPendingIdentity({phone:{...status.network?.phone,label:status.session.device_label},fingerprint:status.session.device_key_fingerprint});}
            }catch(exception){if(!stopped)setError(exception.message||"monitor status unavailable");}
        };
        const id=setInterval(check,1000);
        return()=>{stopped=true;clearInterval(id);};
    },[scanned,onPaired]);

    useEffect(()=>{
        if(!pendingSession)return undefined;
        let stopped=false;
        const check=async()=>{
            try{
                const response=await fetch(`${pendingSession.origin}/api/status`,{cache:"no-store"});
                const status=await response.json();
                if(!stopped&&status.session?.approved)onPaired(pendingSession);
            }catch(exception){if(!stopped)setError(exception.message||"pairing approval unavailable");}
        };
        const id=setInterval(check,500);
        check();
        return()=>{stopped=true;clearInterval(id);};
    },[pendingSession,onPaired]);

    async function reviewPairing(){
        setBusy(true);setError("");setLog(items=>[...items,"Phone QR scanned","Establishing encrypted link..."]);
        try{
            const url=new URL(payload.trim());
            const params=new URLSearchParams(url.hash.slice(1));
            const handle=params.get("pairing_handle"),token=params.get("pairing_token");
            if(!handle||!token)throw Error("pairing fields missing");
            const apiOrigin=params.get("service_origin")||serviceOrigin;
            const native=window.Capacitor?.Plugins?.TracePulseNative;
            const browserIdentity=getBrowserIdentity();
            const identity=native?.getIdentityPublicKey?await native.getIdentityPublicKey():{public_key_b64:base64UrlEncode(browserIdentity.publicKey)};
            const deviceInfo=native?.getDeviceInfo?await native.getDeviceInfo():{model:"TracePulse browser"};
            const begin=await fetch(`${apiOrigin}/api/pairing/begin`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({handle,token})});
            if(!begin.ok){let detail="pairing challenge rejected";try{const body=await begin.json();if(body.error)detail=`pairing challenge rejected: ${body.error}`;}catch{}throw Error(detail);}
            const challenge=await begin.json();
            const expectedFingerprint=params.get("server_key_fingerprint");
            if(expectedFingerprint&&expectedFingerprint!==challenge.server_key_fingerprint)throw Error("server identity mismatch; do not continue");
            const pairKeys=await createX25519KeyPair();
            const shared=deriveX25519SharedSecret(pairKeys.privateKey,base64UrlDecode(challenge.server_public_key_b64));
            const confirmation=await makeClientPairingConfirmation(shared,base64UrlDecode(challenge.challenge_b64));
            setPairingReview({apiOrigin,handle,token,challenge,laptop:challenge.laptop,pairKeys,shared,confirmation,identity,browserIdentity,deviceInfo});
            setBusy(false);
        }catch(exception){setError(exception.message||"pairing review failed");setBusy(false);}
    }

    async function completePairing(){
        setBusy(true);setError("");
        try{
            const {apiOrigin,handle,token,challenge,pairKeys,confirmation,identity,deviceInfo}=pairingReview;
            const deviceLabel=typeof deviceInfo==="string"?deviceInfo:deviceInfo.model||deviceInfo.name||"TracePulse phone";
            const complete=await fetch(`${apiOrigin}/api/pairing/complete`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({handle,token,challenge_b64:challenge.challenge_b64,phone_public_key_b64:base64UrlEncode(pairKeys.publicKey),device_signing_public_key_b64:identity.public_key_b64,client_confirmation_b64:confirmation,device_label:deviceLabel,device_model:deviceLabel})});
            if(!complete.ok)throw Error("pairing completion rejected");
            const result=await complete.json();
            if(!await verifyServerPairingConfirmation(pairingReview.shared,base64UrlDecode(challenge.challenge_b64),result.server_confirmation_b64))throw Error("server confirmation failed");
            setLog(items=>[...items,"Secure link established","Phone executor ready"]);
            setPhoneConfirmed(true);setPendingSession({origin:apiOrigin,sessionId:result.session_id,sessionKey:await deriveSessionKey(pairingReview.shared,base64UrlDecode(result.session_key_salt_b64)),deviceId:result.device_id,identity:pairingReview.browserIdentity});
        }catch(exception){setError(exception.message||"pairing failed");setBusy(false);}
    }

    const acceptOnLaptop=async()=>{
        setBusy(true);
        try{
            const response=await fetch(`${serviceOrigin}/api/pairing/approve`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
            if(!response.ok)throw Error("laptop approval failed");
            onPaired({origin:serviceOrigin,dashboardOnly:true});
        }catch(exception){setError(exception.message||"laptop approval failed");setBusy(false);}
    };

    if(!showStart)return <StartupScreen/>;
    if(scanned&&phoneConfirmed)return <main className="phone-pairing-success">
        <header><strong>TRACEPULSE</strong><span>03&nbsp; / &nbsp;LINK ESTABLISHED</span></header>
        <section className="pairing-success-content"><div className="pairing-success-mark" aria-hidden="true">✓</div><h1>PAIRING SUCCESSFUL</h1><p>Your phone is securely linked to {pairingReview?.laptop?.hostname||pairingReview?.laptop?.device_name||"this laptop"}.</p><section className="pairing-success-details"><strong>DEVICE&nbsp; {pairingReview?.laptop?.hostname||pairingReview?.laptop?.device_name||"LAPTOP"}</strong><span>IP ADDRESS&nbsp; {pairingReview?.laptop?.ip||"Not reported"}</span><b>STATUS&nbsp; WAITING FOR APPROVAL</b></section><div className="pairing-success-wait" aria-live="polite">WAITING FOR LAPTOP APPROVAL</div>{error&&<p className="pairing-success-error">{error}</p>}</section>
    </main>;
    if(scanned)return <main className="start-shell phone-pair-shell"><section className="start-panel pair-progress"><p className="start-eyebrow">TRACEPULSE // SECURE LINK</p><h1>PAIR WITH THIS LAPTOP?</h1><p>{pairingReview?"Review the laptop identity before accepting the encrypted link.":"Verify the laptop identity before continuing."}</p>{pairingReview&&<DeviceIdentity title="LAPTOP IDENTITY" identity={pairingReview.laptop} fingerprint={pairingReview.challenge.server_key_fingerprint}/>} {!pairingReview?<button className="pair-confirm-button" disabled={busy} onClick={reviewPairing}>{busy?"CHECKING…":"REVIEW LAPTOP"}</button>:<button className="pair-confirm-button" disabled={busy} onClick={completePairing}>{busy?"PAIRING…":"ACCEPT PAIRING"}</button>}{error&&<p className="start-error">{error}</p>}</section></main>;
    if(laptopPending)return <main className="pairing-screen pairing-request-screen">
        <div className="pairing-circuit" aria-hidden="true"/>
        <header className="pairing-topbar"><strong>TRACEPULSE</strong><span>02&nbsp; / &nbsp;VERIFY DEVICE</span></header>
        <section className="pairing-request-content">
            <article className="pairing-request-copy"><p>TRUST STARTS HERE</p><h1>One connection.<br/>Only your devices.</h1><div>A phone is requesting access to this laptop. Confirm the device details before approving this secure pairing.</div><span className="pairing-fingerprint-label">DEVICE FINGERPRINT VERIFICATION</span><div className="pairing-request-radar" aria-hidden="true"><i className="pairing-request-ring pairing-request-ring--outer"/><i className="pairing-request-ring pairing-request-ring--middle"/><i className="pairing-request-ring pairing-request-ring--inner"/><i className="pairing-request-laptop">⌂</i><i className="pairing-request-phone">●</i><i className="pairing-request-link"/></div></article>
            <article className="pairing-request-panel"><h2>Pairing request</h2><p>Verify this device before continuing.</p><DeviceIdentity title={pendingIdentity?.phone?.label||"Requesting phone"} identity={pendingIdentity?.phone} fingerprint={pendingIdentity?.fingerprint}/><button className="pairing-approve-button" disabled={busy} onClick={acceptOnLaptop}>{busy?"APPROVING…":"ACCEPT PAIRING"}</button><p className="pairing-request-notice">Only approve devices you recognise. This phone will become a trusted security key for this laptop.</p>{error&&<p className="pairing-error">{error}</p>}</article>
        </section>
    </main>;
    if(phoneMode)return <main className="start-shell phone-pair-shell"><section className="start-panel pair-progress"><p className="start-eyebrow">TRACEPULSE // PHONE EXECUTOR</p><h1>READY TO SCAN</h1><p>TracePulse was unpaired. Scan the new QR code displayed on the laptop to pair again.</p><div className="scan-pulse">◉</div></section></main>;
    return <main className="pairing-screen">
        <div className="pairing-circuit" aria-hidden="true"/>
        <header className="pairing-topbar"><strong>TRACEPULSE</strong><span>01&nbsp; / &nbsp;CONNECT YOUR PHONE</span></header>
        <section className="pairing-content">
            <article className="pairing-instructions"><p>SECURE LINK / SETUP</p><h1>Your phone is<br/>your security key.</h1><div className="pairing-copy">Pair once. Stay protected wherever you work. Your laptop monitors the trusted connection while your phone stays close.</div><ol><li>Scan the QR code with your phone</li><li>Review and accept the pairing request</li><li>Keep your phone nearby to stay unlocked</li></ol><aside><strong>ENCRYPTED BY DESIGN</strong><span>One-time link · TLS 1.3 secure channel</span></aside></article>
            <article className="pairing-qr-panel"><h2>SECURE PAIRING</h2><p>Scan with your phone camera</p>{qr?<img className="pairing-qr" src={qr} alt="TracePulse phone pairing QR code"/>:<div className="pairing-qr-placeholder" aria-live="polite">GENERATING SECURE QR…</div>}<strong className="pairing-qr-status">{qr?"ONE-TIME ENCRYPTED LINK":"PREPARING ONE-TIME LINK"}</strong>{serverKeyFingerprint&&<span className="pairing-fingerprint">SERVER KEY / {serverKeyFingerprint}</span>}{error&&<p className="pairing-error">{error}</p>}</article>
        </section>
    </main>;
}
