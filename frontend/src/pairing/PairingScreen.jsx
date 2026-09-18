import React,{useEffect,useRef,useState} from "react";
import QRCode from "qrcode";
import {base64UrlDecode,base64UrlEncode,createX25519KeyPair,deriveSessionKey,deriveX25519SharedSecret,getBrowserIdentity,makeClientPairingConfirmation,verifyServerPairingConfirmation} from "../security/crypto";

const serviceOrigin=import.meta.env.VITE_SERVICE_URL||`https://${location.hostname}:8443`;

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
                const source=new URL(offer.qr_payload);
                const params=new URLSearchParams(source.hash.slice(1));
                params.set("service_origin",serviceOrigin);
                const pairingUrl=`${location.origin}${location.pathname}?role=phone#${params}`;
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
                if(!stopped&&status.session?.active&&!status.session?.approved)setLaptopPending(true);
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

    async function pair(){
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
            const deviceInfo=native?.getDeviceInfo?await native.getDeviceInfo():{model:navigator.userAgent};
            const begin=await fetch(`${apiOrigin}/api/pairing/begin`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({handle,token})});
            if(!begin.ok){let detail="pairing challenge rejected";try{const body=await begin.json();if(body.error)detail=`pairing challenge rejected: ${body.error}`;}catch{}throw Error(detail);}
            const challenge=await begin.json();
            const pairKeys=await createX25519KeyPair();
            const shared=deriveX25519SharedSecret(pairKeys.privateKey,base64UrlDecode(challenge.server_public_key_b64));
            const confirmation=await makeClientPairingConfirmation(shared,base64UrlDecode(challenge.challenge_b64));
            const complete=await fetch(`${apiOrigin}/api/pairing/complete`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({handle,token,challenge_b64:challenge.challenge_b64,phone_public_key_b64:base64UrlEncode(pairKeys.publicKey),device_signing_public_key_b64:identity.public_key_b64,client_confirmation_b64:confirmation,device_label:deviceInfo.model||"TracePulse phone",device_model:deviceInfo.model||"unknown"})});
            if(!complete.ok)throw Error("pairing completion rejected");
            const result=await complete.json();
            if(!await verifyServerPairingConfirmation(shared,base64UrlDecode(challenge.challenge_b64),result.server_confirmation_b64))throw Error("server confirmation failed");
            setLog(items=>[...items,"Secure link established","Phone executor ready"]);
            setPendingSession({origin:apiOrigin,sessionId:result.session_id,sessionKey:await deriveSessionKey(shared,base64UrlDecode(result.session_key_salt_b64)),deviceId:result.device_id,identity:browserIdentity});
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
    if(scanned)return <main className="start-shell phone-pair-shell"><section className="start-panel pair-progress"><p className="start-eyebrow">TRACEPULSE // SECURE LINK</p><h1>PAIR WITH THIS LAPTOP?</h1><p>Confirm to establish the encrypted TracePulse phone executor link.</p>{!phoneConfirmed?<button className="pair-confirm-button" disabled={busy} onClick={()=>{setPhoneConfirmed(true);pair();}}>{busy?"PAIRING…":"ACCEPT PAIRING"}</button>:<><div className="scan-pulse">◉</div><p>Phone accepted. Waiting for laptop confirmation before opening the dashboard.</p></>}{error&&<p className="start-error">{error}</p>}</section></main>;
    if(laptopPending)return <main className="start-shell phone-pair-shell"><section className="start-panel pair-progress"><p className="start-eyebrow">TRACEPULSE // LAPTOP APPROVAL</p><h1>PHONE PAIRING REQUEST</h1><p>A phone has accepted the QR pairing request. Confirm this trusted device on the laptop.</p><button className="pair-confirm-button" disabled={busy} onClick={acceptOnLaptop}>{busy?"APPROVING…":"ACCEPT PAIRING"}</button></section></main>;
    if(phoneMode)return <main className="start-shell phone-pair-shell"><section className="start-panel pair-progress"><p className="start-eyebrow">TRACEPULSE // PHONE EXECUTOR</p><h1>READY TO SCAN</h1><p>TracePulse was unpaired. Scan the new QR code displayed on the laptop to pair again.</p><div className="scan-pulse">◉</div></section></main>;
    return <main className="pairing-screen">
        <div className="pairing-circuit" aria-hidden="true"/>
        <header className="pairing-topbar"><strong>TRACEPULSE</strong><span>01&nbsp; / &nbsp;CONNECT YOUR PHONE</span></header>
        <section className="pairing-content">
            <article className="pairing-instructions"><p>SECURE LINK / SETUP</p><h1>Your phone is<br/>your security key.</h1><div className="pairing-copy">Pair once. Stay protected wherever you work. Your laptop monitors the trusted connection while your phone stays close.</div><ol><li>Scan the QR code with your phone</li><li>Review and accept the pairing request</li><li>Keep your phone nearby to stay unlocked</li></ol><aside><strong>ENCRYPTED BY DESIGN</strong><span>One-time link · TLS 1.3 secure channel</span></aside></article>
            <article className="pairing-qr-panel"><h2>SECURE PAIRING</h2><p>Scan with your phone camera</p>{qr?<img className="pairing-qr" src={qr} alt="TracePulse phone pairing QR code"/>:<div className="pairing-qr-placeholder" aria-live="polite">GENERATING SECURE QR…</div>}<strong className="pairing-qr-status">{qr?"ONE-TIME ENCRYPTED LINK":"PREPARING ONE-TIME LINK"}</strong>{error&&<p className="pairing-error">{error}</p>}</article>
        </section>
    </main>;
}
