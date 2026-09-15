import React,{useEffect,useState} from "react";
import {signBrowserUnlockAssertion} from "../security/crypto";

export default function MobileDashboard({session,socket,onUnpair}) {
    const [connected,setConnected]=useState(false);
    const [locked,setLocked]=useState(false);
    const [unlockEnabled,setUnlockEnabled]=useState(false);
    const [message,setMessage]=useState("Secure executor ready");
    const [busy,setBusy]=useState(false);

    useEffect(()=>{
        const removeConnection=socket.onConnection(()=>setConnected(true));
        const removeDisconnect=socket.onDisconnect(()=>{setConnected(false);setMessage("Secure channel offline");});
        return()=>{removeConnection();removeDisconnect();};
    },[socket]);

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

    return <main className="phone-shell"><section className="phone-panel">
        <header className="phone-header"><p className="phone-eyebrow">TRACEPULSE // PHONE EXECUTOR</p><h1>SECURITY CONTROL</h1><span className={connected?"phone-online":"phone-offline"}>● {connected?"CONNECTED":"OFFLINE"}</span><button className="phone-unpair-button" onClick={onUnpair}>UNPAIR</button></header>
        <div className={`phone-notice ${locked?"phone-locked":"phone-ready"}`}><span className="phone-notice-icon">{locked?"🔒":"✓"}</span><div><strong>{locked?"DEVICE LOCKED":"DEVICE PROTECTED"}</strong><p>{message}</p></div></div>
        {locked&&<button className="phone-unlock-button toggle-no" disabled={!connected||busy} onClick={toggleUnlock}><span className="phone-toggle-track"><span className="phone-toggle-knob"/></span>{busy?"REQUESTING UNLOCK…":"UNLOCK KALI SCREEN"}</button>}
        <button className="phone-lock-button" disabled={!connected||busy} onClick={lock}>{busy?"PROCESSING…":"LOCK NOW"}</button>
        <p className="phone-help">{locked?"Press UNLOCK KALI SCREEN to restore the laptop and stop lock enforcement.":"Laptop restored. Lock enforcement is stopped until you press LOCK NOW again."}</p>
    </section></main>;
}
