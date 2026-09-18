import React,{useEffect,useState} from "react";
import EventLog from "../components/EventLog";
import {signBrowserUnlockAssertion} from "../security/crypto";

const value=(item,fallback="—")=>item===undefined||item===null||item===""?fallback:item;
function Metric({label,children,alert=false}){return <article className={`mobile-metric${alert?" mobile-metric-alert":""}`}><span>{label}</span><strong>{children}</strong></article>;}
function LockingScreen(){return <main className="mobile-locking-screen" aria-live="polite"><header className="mobile-locking-header"><strong>TRACEPULSE</strong><span>LOCK COMMAND</span></header><section className="mobile-locking-content"><h1>SENDING LOCK COMMAND…</h1><p>Securing your laptop. Please wait.</p><div className="mobile-locking-orbits" aria-hidden="true"><i/><i/><strong>LOCK</strong></div><section className="mobile-locking-progress"><strong>✓&nbsp; Authenticating device</strong><strong>✓&nbsp; Sending encrypted command</strong><b>○&nbsp; Waiting for OS confirmation</b><span>○&nbsp; Verifying lock state</span></section><small>DO NOT CLOSE THE APP</small></section></main>;}
function LockedStateScreen({device,reason,statusConfirmed,connected,busy,onUnlock}){return <main className="mobile-locked-state"><header className="mobile-locked-header"><strong>TRACEPULSE</strong><span>{statusConfirmed?"OS-CONFIRMED STATE":"LOCK CONFIRMED"}</span></header><section className="mobile-locked-content"><h1>DEVICE LOCKED</h1><p>{device} has been locked successfully.</p><section className="mobile-locked-details" aria-label="Lock details"><span>DEVICE&nbsp; {device}</span><span>REASON&nbsp; {reason}</span><b>STATUS&nbsp; {statusConfirmed?"OS CONFIRMED":"LOCK CONFIRMED"}</b></section><button className="mobile-locked-unlock" type="button" onClick={onUnlock} disabled={!connected||busy}>{busy?"REQUESTING…":"UNLOCK WITH DEVICE CREDENTIAL"}</button></section></main>;}
function MobileNavigation({active,onHome,onSettings}){return <nav className="mobile-bottom-nav" aria-label="Mobile dashboard navigation"><button className={active==="home"?"mobile-nav-active":""} type="button" onClick={onHome}>HOME</button><span>DEVICES</span><span>LOGS</span><button className={active==="settings"?"mobile-nav-active":""} type="button" onClick={onSettings}>SETTINGS</button></nav>;}
function SettingsScreen({status,perimeter,heartbeat,connected,onHome,onSettings}){const laptop=status?.network?.laptop||{};const grace=perimeter.lock_delay_seconds;const range=perimeter.limit_meters;const heartbeatState=heartbeat.expired===true?"EXPIRED":connected?"ACTIVE":"OFFLINE";return <main className="mobile-settings"><header className="mobile-settings-header"><strong>TRACEPULSE</strong></header><section className="mobile-settings-content"><h1>SETTINGS</h1><p>Security &amp; system preferences</p><section className="mobile-settings-section"><h2>PAIRED DEVICE</h2><article className="mobile-settings-device"><strong>{value(laptop.hostname,"LAPTOP").toUpperCase()}</strong><span>{value(laptop.ip,"NOT REPORTED")}</span></article></section><section className="mobile-settings-section"><h2>SECURITY</h2><div className="mobile-settings-rows"><div><span>AUTOMATIC LOCK</span><b>NOT REPORTED</b></div><div><span>LOCK GRACE PERIOD</span><b>{grace==null?"NOT REPORTED":`${grace} SEC`}</b></div><div><span>PROXIMITY RANGE</span><b>{range==null?"NOT REPORTED":`${range} M`}</b></div><div><span>HEARTBEAT</span><b className={heartbeatState==="ACTIVE"?"mobile-settings-safe":""}>{heartbeatState}</b></div><div><span>NOTIFICATIONS</span><b>NOT REPORTED</b></div></div></section><section className="mobile-settings-section mobile-settings-about"><h2>ABOUT</h2><article><span>APP VERSION 1.0.0</span><strong>PRIVACY &amp; SECURITY</strong></article></section></section><MobileNavigation active="settings" onHome={onHome} onSettings={onSettings}/></main>;}

export default function MobileDashboard({session,socket,onUnpair}) {
    const [status,setStatus]=useState(null);
    const [events,setEvents]=useState([]);
    const [connected,setConnected]=useState(false);
    const [locked,setLocked]=useState(false);
    const [unlockEnabled,setUnlockEnabled]=useState(false);
    const [message,setMessage]=useState("Secure executor ready");
    const [busy,setBusy]=useState(false);
    const [confirmOpen,setConfirmOpen]=useState(false);
    const [mobileView,setMobileView]=useState("home");

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

    const perimeter=status?.perimeter||{};const statusLocked=status?.state==="locked";const heartbeat=status?.heartbeat||{};const safe=perimeter.inside===true&&!heartbeat.expired;
    const confirmLock=()=>{lock();setConfirmOpen(false);};
    if(confirmOpen)return <main className="mobile-dashboard mobile-lock-confirmation"><header className="mobile-confirmation-header"><strong>TRACEPULSE</strong><span>LOCK REQUEST</span></header><section className="mobile-confirmation-content"><h1>LOCK LAPTOP?</h1><p>This will immediately lock your paired laptop.</p><section className="mobile-danger-summary"><strong>{value(status?.network?.laptop?.hostname,"LAPTOP").toUpperCase()}</strong><span>CURRENT STATUS&nbsp; {connected?"CONNECTED":"OFFLINE"}</span><span>DISTANCE&nbsp; {value(perimeter.distance_meters)} m</span><b>CONFIRMATION REQUIRED</b></section><button className="mobile-confirm-lock" disabled={!connected||busy} onClick={confirmLock}>YES, LOCK NOW</button><button className="mobile-confirm-cancel" onClick={()=>setConfirmOpen(false)}>CANCEL</button></section></main>;
    if(locked||statusLocked)return <LockedStateScreen device={value(status?.network?.laptop?.hostname,"Laptop")} reason={value(status?.decision?.reason,"Not reported")} statusConfirmed={statusLocked} connected={connected} busy={busy} onUnlock={unlock}/>;
    if(busy&&!locked)return <LockingScreen/>;
    if(mobileView==="settings")return <SettingsScreen status={status} perimeter={perimeter} heartbeat={heartbeat} connected={connected} onHome={()=>setMobileView("home")} onSettings={()=>setMobileView("settings")}/>;
    return <main className="mobile-dashboard"><header className="mobile-dashboard-header"><div><p>TRACEPULSE // PHONE DASHBOARD</p><h1>Security overview</h1><span className={connected?"mobile-online":"mobile-offline"}>● {connected?"CONNECTED":"OFFLINE"}</span></div><button onClick={onUnpair}>UNPAIR</button></header>
        <section className="mobile-status-hero"><div><span className={safe?"mobile-safe":"mobile-alert"}>● {safe?"PROTECTED":"ATTENTION"}</span><h2>{locked?"DEVICE LOCKED":"DEVICE PROTECTED"}</h2><p>{message}</p></div><strong>{value(status?.state,"STARTING").toUpperCase()}</strong></section>
        <section className="mobile-metrics"><Metric label="Phone heartbeat" alert={heartbeat.expired}>{heartbeat.expired?"EXPIRED":"HEALTHY"}</Metric><Metric label="Perimeter" alert={!perimeter.inside}>{perimeter.inside?"INSIDE":"OUTSIDE"}</Metric><Metric label="Distance">{value(perimeter.distance_meters)} m</Metric><Metric label="Signal">{perimeter.rssi_dbm==null?"—":`${perimeter.rssi_dbm} dBm`}</Metric></section>
        <section className="mobile-dashboard-grid"><section className="mobile-panel"><h2>Proximity Guard</h2><p>Security boundary: <strong>{value(perimeter.limit_meters)} m</strong></p><div className={`mobile-range ${perimeter.inside?"mobile-range-safe":"mobile-range-alert"}`}><span>⌂</span><i/><b>{value(perimeter.distance_meters)}</b><small>metres</small></div><p>Lock delay: <strong>{value(perimeter.lock_delay_seconds)} seconds</strong></p></section><section className="mobile-panel"><h2>System information</h2><dl><div><dt>Laptop</dt><dd>{value(status?.network?.laptop?.hostname)}</dd></div><div><dt>IP address</dt><dd>{value(status?.network?.laptop?.ip)}</dd></div><div><dt>Paired device</dt><dd>{value(status?.session?.device_label)}</dd></div><div><dt>Audit</dt><dd>{status?.audit?.valid?"VALID":"UNKNOWN"}</dd></div></dl></section></section>
        <EventLog events={events}/><section className="mobile-actions"><button className="mobile-lock" disabled={!connected||busy} onClick={()=>setConfirmOpen(true)}>LOCK NOW</button>{locked&&<button className="mobile-unlock" disabled={!connected||busy} onClick={unlock}>{busy?"REQUESTING…":"UNLOCK DEVICE"}</button>}</section><div className="mobile-home-nav"><MobileNavigation active="home" onHome={()=>setMobileView("home")} onSettings={()=>setMobileView("settings")}/></div>
    </main>;
}
