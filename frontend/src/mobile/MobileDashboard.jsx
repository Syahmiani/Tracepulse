import React,{useEffect,useState} from "react";
import EventLog from "../components/EventLog";
import {signBrowserUnlockAssertion} from "../security/crypto";

const value=(item,fallback="—")=>item===undefined||item===null||item===""?fallback:item;
function Metric({label,children,alert=false}){return <article className={`mobile-metric${alert?" mobile-metric-alert":""}`}><span>{label}</span><strong>{children}</strong></article>;}

export default function MobileDashboard({session,socket,onUnpair}) {
    const [status,setStatus]=useState(null);
    const [events,setEvents]=useState([]);
    const [connected,setConnected]=useState(false);
    const [locked,setLocked]=useState(false);
    const [unlockEnabled,setUnlockEnabled]=useState(false);
    const [message,setMessage]=useState("Secure executor ready");
    const [busy,setBusy]=useState(false);

    useEffect(()=>{
        let stopped=false;
        const refresh=async()=>{try{const response=await fetch(`${session.origin}/api/status`,{cache:"no-store"});if(!response.ok)throw Error("monitor status unavailable");if(!stopped)setStatus(await response.json());}catch(error){if(!stopped)setMessage(error.message);}};
        refresh();const id=setInterval(refresh,1000);return()=>{stopped=true;clearInterval(id);};
    },[session.origin]);

    useEffect(()=>{
        const removeConnection=socket.onConnection(()=>setConnected(true));
        const removeDisconnect=socket.onDisconnect(()=>{setConnected(false);setMessage("Secure channel offline");});
        const removeMessages=socket.onSecureMessage(async event=>{
            setEvents(current=>[event,...current].slice(0,50));
            if(event.event==="lock_result"){const confirmed=event.payload?.confirmed===true;setLocked(confirmed);if(confirmed)setUnlockEnabled(false);setMessage(confirmed?"Workstation locked":"Lock request was not confirmed");setBusy(false);}
            if(event.event==="unlock_challenge"){
                try{const native=window.Capacitor?.Plugins?.TracePulseNative;const now=Math.floor(Date.now()/1000);const nativeResult=native?.authorizeUnlock?await native.authorizeUnlock({nonce:event.payload.nonce,sessionId:session.sessionId}):null;const assertion=nativeResult?.assertion||nativeResult||{nonce:event.payload.nonce,verification_id:"browser-demo",issued_at_epoch:now,expires_at_epoch:now+30,signature_b64:signBrowserUnlockAssertion({privateKey:session.identity.privateKey,sessionId:session.sessionId,nonce:event.payload.nonce,verificationId:"browser-demo",issuedAt:now,expiresAt:now+30})};await socket.send("unlock_request",{assertion});}catch(error){setBusy(false);setMessage(error.message);}
            }
            if(event.event==="unlock_result"){const confirmed=event.payload?.confirmed===true;setLocked(!confirmed);setUnlockEnabled(confirmed);setMessage(confirmed?"Workstation restored":"Unlock request was not confirmed");setBusy(false);}
        });
        return()=>{removeConnection();removeDisconnect();removeMessages();};
    },[socket,session]);

    useEffect(()=>{
        if(!connected)return undefined;
        const heartbeat=setInterval(()=>socket.send("heartbeat",{}).catch(error=>setMessage(error.message)),400);
        return()=>clearInterval(heartbeat);
    },[connected,socket]);

    useEffect(()=>socket.onSecureMessage(async event=>{
        if(event.event==="lock_result"){
            const confirmed=event.payload?.confirmed===true;
            setLocked(confirmed);
            if(confirmed)setUnlockEnabled(false);
            setMessage(confirmed?"Kali workstation locked":"Kali lock request was not confirmed");
            setBusy(false);
            return;
        }
        if(event.event==="unlock_challenge"){
            try{
                const native=window.Capacitor?.Plugins?.TracePulseNative;
                const now=Math.floor(Date.now()/1000);
                const nativeResult=native?.authorizeUnlock
                    ? await native.authorizeUnlock({nonce:event.payload.nonce,sessionId:session.sessionId})
                    : null;
                const assertion=nativeResult?.assertion||nativeResult||{nonce:event.payload.nonce,verification_id:"browser-demo",issued_at_epoch:now,expires_at_epoch:now+30,signature_b64:signBrowserUnlockAssertion({privateKey:session.identity.privateKey,sessionId:session.sessionId,nonce:event.payload.nonce,verificationId:"browser-demo",issuedAt:now,expiresAt:now+30})};
                await socket.send("unlock_request",{assertion});
            }catch(error){setBusy(false);setMessage(error.message);}
            return;
        }
        if(event.event==="unlock_result"){
            const confirmed=event.payload?.confirmed===true;
            setLocked(!confirmed);
            setUnlockEnabled(confirmed);
            setMessage(confirmed?"Laptop restored. Kali can now be opened normally.":"Kali unlock request was not confirmed");
            setBusy(false);
        }
    }),[socket,session.sessionId]);

    const lock=()=>{
        setBusy(true);setMessage("Locking Kali workstation...");
        socket.send("lock_request",{reason:"phone emergency lock"}).catch(error=>{setBusy(false);setMessage(error.message);});
    };
    const unlock=()=>{
        setBusy(true);setMessage("Requesting Kali unlock screen...");
        socket.send("unlock_challenge_request",{}).catch(error=>{setBusy(false);setMessage(error.message);});
    };
    const toggleUnlock=()=>{
        if(unlockEnabled){
            setUnlockEnabled(false);
            setBusy(true);
            setMessage("Lock hold enabled. Locking Kali workstation...");
            socket.send("lock_request",{reason:"unlock toggle set to no"}).catch(error=>{setBusy(false);setMessage(error.message);});
            return;
        }
        unlock();
    };

    const perimeter=status?.perimeter||{};const heartbeat=status?.heartbeat||{};const safe=perimeter.inside===true&&!heartbeat.expired;
    return <main className="mobile-dashboard"><header className="mobile-dashboard-header"><div><p>TRACEPULSE // PHONE DASHBOARD</p><h1>Security overview</h1><span className={connected?"mobile-online":"mobile-offline"}>● {connected?"CONNECTED":"OFFLINE"}</span></div><button onClick={onUnpair}>UNPAIR</button></header>
        <section className="mobile-status-hero"><div><span className={safe?"mobile-safe":"mobile-alert"}>● {safe?"PROTECTED":"ATTENTION"}</span><h2>{locked?"DEVICE LOCKED":"DEVICE PROTECTED"}</h2><p>{message}</p></div><strong>{value(status?.state,"STARTING").toUpperCase()}</strong></section>
        <section className="mobile-metrics"><Metric label="Phone heartbeat" alert={heartbeat.expired}>{heartbeat.expired?"EXPIRED":"HEALTHY"}</Metric><Metric label="Perimeter" alert={!perimeter.inside}>{perimeter.inside?"INSIDE":"OUTSIDE"}</Metric><Metric label="Distance">{value(perimeter.distance_meters)} m</Metric><Metric label="Signal">{perimeter.rssi_dbm==null?"—":`${perimeter.rssi_dbm} dBm`}</Metric></section>
        <section className="mobile-dashboard-grid"><section className="mobile-panel"><h2>Proximity Guard</h2><p>Security boundary: <strong>{value(perimeter.limit_meters)} m</strong></p><div className={`mobile-range ${perimeter.inside?"mobile-range-safe":"mobile-range-alert"}`}><span>⌂</span><i/><b>{value(perimeter.distance_meters)}</b><small>metres</small></div><p>Lock delay: <strong>{value(perimeter.lock_delay_seconds)} seconds</strong></p></section><section className="mobile-panel"><h2>System information</h2><dl><div><dt>Laptop</dt><dd>{value(status?.network?.laptop?.hostname)}</dd></div><div><dt>IP address</dt><dd>{value(status?.network?.laptop?.ip)}</dd></div><div><dt>Paired device</dt><dd>{value(status?.session?.device_label)}</dd></div><div><dt>Audit</dt><dd>{status?.audit?.valid?"VALID":"UNKNOWN"}</dd></div></dl></section></section>
        <EventLog events={events}/><section className="mobile-actions"><button className="mobile-lock" disabled={!connected||busy} onClick={lock}>{busy?"PROCESSING…":"LOCK NOW"}</button>{locked&&<button className="mobile-unlock" disabled={!connected||busy} onClick={unlock}>{busy?"REQUESTING…":"UNLOCK DEVICE"}</button>}</section>
    </main>;
}
