import React,{useEffect,useState} from "react";
import EventLog from "../components/EventLog";
import {signBrowserUnlockAssertion} from "../security/crypto";

const value=(item,fallback="—")=>item===undefined||item===null||item===""?fallback:item;
function Metric({label,children,alert=false}){return <article className={`mobile-metric${alert?" mobile-metric-alert":""}`}><span>{label}</span><strong>{children}</strong></article>;}
const activityTitle=event=>String(event||"security event").replace(/[_-]/g," ").toUpperCase();
const activityDetail=(payload={})=>payload.reason||payload.confirmed===true?payload.reason||"Action confirmed":payload.confirmed===false?"Action was not confirmed":"Authenticated security event";
const activityTime=timestamp=>timestamp?new Date(timestamp).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):"LIVE";
const activityTone=event=>/lock|fail|denied/i.test(event)?"mobile-log-alert":/heartbeat|pair|channel|unlock/i.test(event)?"mobile-log-safe":"mobile-log-neutral";
function LockingScreen(){return <main className="mobile-locking-screen" aria-live="polite"><header className="mobile-locking-header"><strong>TRACEPULSE</strong><span>LOCK COMMAND</span></header><section className="mobile-locking-content"><h1>SENDING LOCK COMMAND…</h1><p>Securing your laptop. Please wait.</p><div className="mobile-locking-orbits" aria-hidden="true"><i/><i/><strong>LOCK</strong></div><section className="mobile-locking-progress"><strong>✓&nbsp; Authenticating device</strong><strong>✓&nbsp; Sending encrypted command</strong><b>○&nbsp; Waiting for OS confirmation</b><span>○&nbsp; Verifying lock state</span></section><small>DO NOT CLOSE THE APP</small></section></main>;}
function LockedStateScreen({device,reason,statusConfirmed,connected,busy,onUnlock}){return <main className="mobile-locked-state"><header className="mobile-locked-header"><strong>TRACEPULSE</strong><span>{statusConfirmed?"OS-CONFIRMED STATE":"LOCK CONFIRMED"}</span></header><section className="mobile-locked-content"><h1>DEVICE LOCKED</h1><p>{device} has been locked successfully.</p><section className="mobile-locked-details" aria-label="Lock details"><span>DEVICE&nbsp; {device}</span><span>REASON&nbsp; {reason}</span><b>STATUS&nbsp; {statusConfirmed?"OS CONFIRMED":"LOCK CONFIRMED"}</b></section><button className="mobile-locked-unlock" type="button" onClick={onUnlock} disabled={!connected||busy}>{busy?"REQUESTING…":"UNLOCK WITH DEVICE CREDENTIAL"}</button></section></main>;}
function MobileNavigation({active,onHome,onDevices,onLogs,onSettings}){return <nav className="mobile-bottom-nav" aria-label="Mobile dashboard navigation"><button className={active==="home"?"mobile-nav-active":""} type="button" onClick={onHome}>HOME</button><button className={active==="devices"?"mobile-nav-active":""} type="button" onClick={onDevices}>DEVICES</button><button className={active==="logs"?"mobile-nav-active":""} type="button" onClick={onLogs}>LOGS</button><button className={active==="settings"?"mobile-nav-active":""} type="button" onClick={onSettings}>SETTINGS</button></nav>;}
function SettingsScreen({status,perimeter,heartbeat,connected,onHome,onDevices,onLogs,onSettings}){const laptop=status?.network?.laptop||{};const grace=perimeter.lock_delay_seconds;const range=perimeter.limit_meters;const heartbeatState=heartbeat.expired===true?"EXPIRED":connected?"ACTIVE":"OFFLINE";return <main className="mobile-settings"><header className="mobile-settings-header"><strong>TRACEPULSE</strong></header><section className="mobile-settings-content"><h1>SETTINGS</h1><p>Security &amp; system preferences</p><section className="mobile-settings-section"><h2>PAIRED DEVICE</h2><article className="mobile-settings-device"><strong>{value(laptop.hostname,"LAPTOP").toUpperCase()}</strong><span>{value(laptop.ip,"NOT REPORTED")}</span></article></section><section className="mobile-settings-section"><h2>SECURITY</h2><div className="mobile-settings-rows"><div><span>AUTOMATIC LOCK</span><b>NOT REPORTED</b></div><div><span>LOCK GRACE PERIOD</span><b>{grace==null?"NOT REPORTED":`${grace} SEC`}</b></div><div><span>PROXIMITY RANGE</span><b>{range==null?"NOT REPORTED":`${range} M`}</b></div><div><span>HEARTBEAT</span><b className={heartbeatState==="ACTIVE"?"mobile-settings-safe":""}>{heartbeatState}</b></div><div><span>NOTIFICATIONS</span><b>NOT REPORTED</b></div></div></section><section className="mobile-settings-section mobile-settings-about"><h2>ABOUT</h2><article><span>APP VERSION 1.0.0</span><strong>PRIVACY &amp; SECURITY</strong></article></section></section><MobileNavigation active="settings" onHome={onHome} onDevices={onDevices} onLogs={onLogs} onSettings={onSettings}/></main>;}
function DevicesScreen({status,heartbeat,connected,onUnpair,navigation}){const laptop=status?.network?.laptop||{};const pairing=status?.session?.approved===true?"APPROVED":status?.session?.active===true?"ACTIVE":"NOT REPORTED";const heartbeatState=heartbeat.expired===true?"EXPIRED":connected?"ACTIVE":"OFFLINE";return <main className="mobile-devices"><header className="mobile-devices-header"><strong>TRACEPULSE</strong></header><section className="mobile-devices-content"><h1>DEVICES</h1><p>Trusted &amp; paired workstation</p><article className="mobile-device-card"><i aria-hidden="true">▣</i><div><strong>{value(laptop.hostname,"LAPTOP").toUpperCase()}</strong><b className={connected?"mobile-devices-safe":"mobile-devices-alert"}>● {connected?"CONNECTED":"OFFLINE"}</b><span>{value(laptop.ip,"NOT REPORTED")}</span></div><em aria-hidden="true">›</em></article><section className="mobile-devices-section"><h2>SECURE CONNECTION</h2><article className="mobile-devices-details"><div><span>SECURE CHANNEL</span><b className={connected?"mobile-devices-safe":"mobile-devices-alert"}>{connected?"CONNECTED":"OFFLINE"}</b></div><div><span>HEARTBEAT</span><b className={heartbeatState==="ACTIVE"?"mobile-devices-safe":"mobile-devices-alert"}>{heartbeatState}</b></div></article></section><section className="mobile-devices-section"><h2>DEVICE SECURITY</h2><article className="mobile-devices-details"><div><span>PAIRING STATUS</span><b className={pairing==="APPROVED"||pairing==="ACTIVE"?"mobile-devices-safe":""}>{pairing}</b></div><div><span>DEVICE CREDENTIALS</span><b className="mobile-devices-safe">READY</b></div></article></section><button className="mobile-device-details" type="button" disabled>VIEW DEVICE DETAILS</button><button className="mobile-device-unpair" type="button" onClick={onUnpair}>UNPAIR DEVICE</button></section><MobileNavigation active="devices" {...navigation}/></main>;}
function LogsScreen({events,navigation}){return <main className="mobile-activity-logs"><header className="mobile-logs-header"><strong>TRACEPULSE</strong></header><section className="mobile-logs-content"><h1>ACTIVITY LOGS</h1><p>Verified security activity</p><span className="mobile-logs-filter">ALL</span><section className="mobile-log-list" aria-live="polite">{events.length===0?<p className="mobile-log-empty">Waiting for authenticated security events.</p>:events.map((event,index)=><article className="mobile-log-entry" key={`${event.nonce||event.timestamp_ms||"event"}-${index}`}><time>{activityTime(event.timestamp_ms)}</time><div><strong className={activityTone(event.event)}>{activityTitle(event.event)}</strong><span>{activityDetail(event.payload)}</span><small>AUTHENTICATED EVENT</small></div></article>)}</section></section><MobileNavigation active="logs" {...navigation}/></main>;}

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
    const navigation={onHome:()=>setMobileView("home"),onDevices:()=>setMobileView("devices"),onLogs:()=>setMobileView("logs"),onSettings:()=>setMobileView("settings")};
    const confirmLock=()=>{lock();setConfirmOpen(false);};
    if(confirmOpen)return <main className="mobile-dashboard mobile-lock-confirmation"><header className="mobile-confirmation-header"><strong>TRACEPULSE</strong><span>LOCK REQUEST</span></header><section className="mobile-confirmation-content"><h1>LOCK LAPTOP?</h1><p>This will immediately lock your paired laptop.</p><section className="mobile-danger-summary"><strong>{value(status?.network?.laptop?.hostname,"LAPTOP").toUpperCase()}</strong><span>CURRENT STATUS&nbsp; {connected?"CONNECTED":"OFFLINE"}</span><span>DISTANCE&nbsp; {value(perimeter.distance_meters)} m</span><b>CONFIRMATION REQUIRED</b></section><button className="mobile-confirm-lock" disabled={!connected||busy} onClick={confirmLock}>YES, LOCK NOW</button><button className="mobile-confirm-cancel" onClick={()=>setConfirmOpen(false)}>CANCEL</button></section></main>;
    if(locked||statusLocked)return <LockedStateScreen device={value(status?.network?.laptop?.hostname,"Laptop")} reason={value(status?.decision?.reason,"Not reported")} statusConfirmed={statusLocked} connected={connected} busy={busy} onUnlock={unlock}/>;
    if(busy&&!locked)return <LockingScreen/>;
    if(mobileView==="devices")return <DevicesScreen status={status} heartbeat={heartbeat} connected={connected} onUnpair={onUnpair} navigation={navigation}/>;
    if(mobileView==="logs")return <LogsScreen events={events} navigation={navigation}/>;
    if(mobileView==="settings")return <SettingsScreen status={status} perimeter={perimeter} heartbeat={heartbeat} connected={connected} {...navigation}/>;
    return <main className="mobile-dashboard"><header className="mobile-dashboard-header"><div><p>TRACEPULSE // PHONE DASHBOARD</p><h1>Security overview</h1><span className={connected?"mobile-online":"mobile-offline"}>● {connected?"CONNECTED":"OFFLINE"}</span></div><button onClick={onUnpair}>UNPAIR</button></header>
        <section className="mobile-status-hero"><div><span className={safe?"mobile-safe":"mobile-alert"}>● {safe?"PROTECTED":"ATTENTION"}</span><h2>{locked?"DEVICE LOCKED":"DEVICE PROTECTED"}</h2><p>{message}</p></div><strong>{value(status?.state,"STARTING").toUpperCase()}</strong></section>
        <section className="mobile-metrics"><Metric label="Phone heartbeat" alert={heartbeat.expired}>{heartbeat.expired?"EXPIRED":"HEALTHY"}</Metric><Metric label="Perimeter" alert={!perimeter.inside}>{perimeter.inside?"INSIDE":"OUTSIDE"}</Metric><Metric label="Distance">{value(perimeter.distance_meters)} m</Metric><Metric label="Signal">{perimeter.rssi_dbm==null?"—":`${perimeter.rssi_dbm} dBm`}</Metric></section>
        <section className="mobile-dashboard-grid"><section className="mobile-panel"><h2>Proximity Guard</h2><p>Security boundary: <strong>{value(perimeter.limit_meters)} m</strong></p><div className={`mobile-range ${perimeter.inside?"mobile-range-safe":"mobile-range-alert"}`}><span>⌂</span><i/><b>{value(perimeter.distance_meters)}</b><small>metres</small></div><p>Lock delay: <strong>{value(perimeter.lock_delay_seconds)} seconds</strong></p></section><section className="mobile-panel"><h2>System information</h2><dl><div><dt>Laptop</dt><dd>{value(status?.network?.laptop?.hostname)}</dd></div><div><dt>IP address</dt><dd>{value(status?.network?.laptop?.ip)}</dd></div><div><dt>Paired device</dt><dd>{value(status?.session?.device_label)}</dd></div><div><dt>Audit</dt><dd>{status?.audit?.valid?"VALID":"UNKNOWN"}</dd></div></dl></section></section>
        <EventLog events={events}/><section className="mobile-actions"><button className="mobile-lock" disabled={!connected||busy} onClick={()=>setConfirmOpen(true)}>LOCK NOW</button>{locked&&<button className="mobile-unlock" disabled={!connected||busy} onClick={unlock}>{busy?"REQUESTING…":"UNLOCK DEVICE"}</button>}</section><div className="mobile-home-nav"><MobileNavigation active="home" {...navigation}/></div>
    </main>;
}
