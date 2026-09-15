import React,{useEffect,useState} from "react";
import EventLog from "../components/EventLog";

const value=(item,fallback="—")=>item===undefined||item===null||item===""?fallback:item;
const age=(epoch)=>epoch?`${Math.max(0,Math.round(Date.now()/1000-epoch))}s ago`:"not observed";

function Metric({label,children,accent=""}){return <article className={`monitor-card ${accent}`}><span className="monitor-label">{label}</span><strong>{children}</strong></article>;}
function DeviceRow({title,device,detail}){return <div className="device-row"><div><b>{title}</b><span>{detail}</span></div><code>MODEL {value(device?.model)}<br/>IP&nbsp; {value(device?.ip)}<br/>MAC {value(device?.mac)}</code></div>;}

export default function LaptopDashboard({session,socket,onUnpair}){
    const [status,setStatus]=useState(null);
    const [events,setEvents]=useState([]);
    const [error,setError]=useState("");
    useEffect(()=>{
        let stopped=false;
        const refresh=async()=>{
            try{const response=await fetch(`${session.origin}/api/status`,{cache:"no-store"});if(!response.ok)throw Error("monitor status unavailable");if(!stopped)setStatus(await response.json());}
            catch(exception){if(!stopped)setError(exception.message);}
        };
        refresh();const id=setInterval(refresh,1000);return()=>{stopped=true;clearInterval(id);};
    },[session.origin]);
    useEffect(()=>socket?.onSecureMessage(message=>setEvents(current=>[message,...current].slice(0,50))),[socket]);
    const perimeter=status?.perimeter||{};
    const network=status?.network||{};
    const heartbeat=status?.heartbeat||{};
    return <main className="monitor-shell">
        <header className="monitor-header">
            <div><p className="eyebrow">TRACEPULSE // KALI MONITOR</p><h1>Security Operations Console</h1><p className="muted">Laptop observes. Paired phone executes authorized actions.</p></div>
            <div className="header-actions"><span className="live-dot">● LIVE</span><button onClick={onUnpair}>UNPAIR</button></div>
        </header>
        {error&&<p className="error-text">{error}</p>}
        <section className="monitor-grid">
            <Metric label="Security state" accent={status?.state==="armed"?"good":"warn"}>{value(status?.state,"STARTING").toUpperCase()}</Metric>
            <Metric label="Phone heartbeat" accent={heartbeat.expired?"danger":"good"}>{heartbeat.expired?"EXPIRED":"HEALTHY"}</Metric>
            <Metric label="Perimeter" accent={perimeter.inside?"good":"danger"}>{perimeter.inside?"INSIDE":"OUTSIDE"}</Metric>
            <Metric label="Audit integrity" accent={status?.audit?.valid?"good":"danger"}>{status?.audit?.valid?"VALID":"INVALID"}</Metric>
        </section>
        <section className="monitor-columns">
            <div className="monitor-main">
                <section className="monitor-panel perimeter-panel">
                    <div className="panel-heading"><div><p className="eyebrow">PROXIMITY GUARD</p><h2>8 meter perimeter</h2></div><span className={`state-pill ${perimeter.inside?"pill-good":"pill-danger"}`}>{perimeter.inside?"PHONE IN RANGE":"RANGE BREACH"}</span></div>
                    <div className="perimeter-meter"><div className="perimeter-ring"><strong>{value(perimeter.distance_meters,"—")}</strong><span>meters</span></div><div className="perimeter-facts"><p><b>Boundary</b><span>{value(perimeter.limit_meters)} m</span></p><p><b>RSSI signal</b><span>{perimeter.rssi_dbm===null?"—":`${value(perimeter.rssi_dbm)} dBm`}</span></p><p><b>Lock delay</b><span>{value(perimeter.lock_delay_seconds)} s continuous</span></p></div></div>
                </section>
                <section className="monitor-panel"><div className="panel-heading"><div><p className="eyebrow">ASSET INVENTORY</p><h2>Paired endpoints</h2></div><span className="muted">{status?.session?.device_label||"awaiting device"}</span></div><div className="device-list"><DeviceRow title="Kali laptop" device={network.laptop} detail={`${network.laptop?.hostname||"local host"} · ${network.laptop?.user||"operator"}`}/><DeviceRow title="TracePulse phone" device={network.phone} detail={`${status?.session?.device_label||"paired device"} · last seen ${age(network.phone?.last_seen_epoch)}`}/></div></section>
                <section className="monitor-panel"><div className="panel-heading"><div><p className="eyebrow">DECISION ENGINE</p><h2>Runtime assessment</h2></div></div><div className="facts-grid"><p><b>Current reason</b><span>{value(status?.decision?.reason,"No decision yet")}</span></p><p><b>Model state</b><span>{value(status?.decision?.model_state)}</span></p><p><b>OS session</b><span>{status?.os_session?.active?"ACTIVE":"UNAVAILABLE"}</span></p><p><b>Session ID</b><span>{value(status?.session?.session_id_prefix)}</span></p></div></section>
            </div>
            <aside className="monitor-side">
                <section className="monitor-panel"><p className="eyebrow">TELEMETRY</p><h2>Live link health</h2><div className="telemetry-list"><p><b>Received heartbeats</b><span>{value(heartbeat.received_count,0)}</span></p><p><b>Heartbeat age</b><span>{heartbeat.age_seconds===null?"—":`${Number(heartbeat.age_seconds).toFixed(1)}s`}</span></p><p><b>Transport</b><span>TLS / WSS</span></p><p><b>BLE adapter</b><span>hci0</span></p></div></section>
                <EventLog events={events}/>
                <section className="monitor-panel operator-note"><p className="eyebrow">OPERATOR MODEL</p><p><b>Phone = executor</b></p><p className="muted">Unlock authorization, heartbeat, and lock actions originate from the paired phone. This console observes telemetry, perimeter decisions, audit integrity, and endpoint identity.</p></section>
            </aside>
        </section>
    </main>;
}
