import React, {useEffect, useState} from "react";
import EventLog from "../components/EventLog";
import StatusCard from "../components/StatusCard";

const value = (item, fallback = "—") => item === undefined || item === null || item === "" ? fallback : item;

function healthTone(healthy) {
    return healthy ? "safe" : "alert";
}

function ProximityRadar({inside, distance}) {
    return <div className={`proximity-radar ${inside ? "is-safe" : "is-alert"}`} aria-label={`Phone ${inside ? "within" : "outside"} the configured security perimeter`}>
        <span className="radar-ring radar-ring--outer"/><span className="radar-ring radar-ring--middle"/><span className="radar-ring radar-ring--inner"/>
        <span className="radar-laptop">⌂</span><span className="radar-phone">●</span><span className="radar-link"/>
        <strong>{value(distance)}</strong><small>metres</small>
    </div>;
}

function RelativeProximity({inside, distance}) {
    return <section className="dashboard-card relative-proximity-card">
        <h2>Signal &amp; proximity</h2><p>Relative range estimate · not GPS location</p>
        <div className={`relative-radar ${inside ? "is-safe" : "is-alert"}`}>
            <span className="relative-ring relative-ring--outer"/><span className="relative-ring relative-ring--inner"/><span className="relative-laptop">⌂</span><span className="relative-phone">●</span><span className="relative-link"/>
        </div>
        <span className="relative-caption">Laptop&nbsp; ● &nbsp;———&nbsp; ●&nbsp; Paired phone · {value(distance)} m</span>
    </section>;
}

function ProximityGuard({perimeter}) {
    const inside = perimeter.inside === true;
    return <section className="dashboard-card proximity-guard">
        <div><h2>Proximity Guard</h2><p>Keep your phone within the configured security range.</p></div>
        <div className="proximity-content">
            <ProximityRadar inside={inside} distance={perimeter.distance_meters}/>
            <div className="proximity-metrics">
                <strong className={inside ? "status-safe" : "status-alert"}>● {inside ? "WITHIN SAFE ZONE" : "RANGE BREACH"}</strong>
                <p><span>Security boundary</span><b>{value(perimeter.limit_meters)} metres</b></p>
                <p><span>Current distance</span><b>{value(perimeter.distance_meters)} metres</b></p>
                <p><span>Signal strength</span><b>{perimeter.rssi_dbm == null ? "—" : `${value(perimeter.rssi_dbm)} dBm`}</b></p>
                <p><span>Lock delay</span><b>{value(perimeter.lock_delay_seconds)} seconds</b></p>
                <p><span>Connection</span><b className="connection-value">TLS / WSS</b></p>
            </div>
        </div>
    </section>;
}

function DecisionCard({status}) {
    const safe = status?.state === "armed" && status?.perimeter?.inside && !status?.heartbeat?.expired;
    const decision = status?.decision || {};
    return <section className="dashboard-card decision-card">
        <h2>AI Decision Engine</h2>
        <strong className={safe ? "status-safe decision-state" : "status-alert decision-state"}>● {safe ? "SAFE" : value(status?.state, "STARTING").toUpperCase()}</strong>
        <p>{value(decision.reason, "Awaiting a runtime assessment.")}</p>
        <span>MODEL STATE / {value(decision.model_state, "MODEL_NOT_READY")}</span>
    </section>;
}

function SystemInformation({status}) {
    const network = status?.network || {};
    return <section className="dashboard-card system-information-card">
        <h2>System information</h2>
        <dl>
            <div><dt>Device</dt><dd>{value(network.laptop?.hostname, "TracePulse Laptop")}</dd></div>
            <div><dt>User</dt><dd>{value(network.laptop?.user)}</dd></div>
            <div><dt>OS session</dt><dd>{status?.os_session?.active ? "Active" : "Unavailable"}</dd></div>
            <div><dt>Paired phone</dt><dd>{value(status?.session?.device_label, "Awaiting device")}</dd></div>
        </dl>
    </section>;
}

export default function LaptopDashboard({session, socket, onUnpair, onShowMobile}) {
    const [status, setStatus] = useState(null);
    const [events, setEvents] = useState([]);
    const [error, setError] = useState("");
    useEffect(() => {
        let stopped = false;
        const refresh = async () => {
            try {
                const response = await fetch(`${session.origin}/api/status`, {cache: "no-store"});
                if (!response.ok) throw Error("monitor status unavailable");
                if (!stopped) setStatus(await response.json());
            } catch (exception) {
                if (!stopped) setError(exception.message);
            }
        };
        refresh();
        const id = setInterval(refresh, 1000);
        return () => { stopped = true; clearInterval(id); };
    }, [session.origin]);
    useEffect(() => socket?.onSecureMessage(message => setEvents(current => [message, ...current].slice(0, 50))), [socket]);

    const perimeter = status?.perimeter || {};
    const heartbeat = status?.heartbeat || {};
    const auditValid = status?.audit?.valid === true;
    const sessionActive = status?.session?.active === true;
    return <main className="security-dashboard">
        <div className="dashboard-circuit" aria-hidden="true"/>
        <aside className="dashboard-sidebar">
            <div className="dashboard-brand"><strong>TRACEPULSE</strong><span>SECURITY WORKSPACE</span></div>
            <nav className="dashboard-navigation" aria-label="Dashboard sections">
                <span className="navigation-item navigation-item--active">OVERVIEW</span><span className="navigation-item">PROXIMITY</span><span className="navigation-item">EVENTS</span><span className="navigation-item">DECISIONS</span><span className="navigation-item">SYSTEM</span>
            </nav>
            <section className="sidebar-protection"><strong className={sessionActive ? "status-safe" : "status-alert"}>● {sessionActive ? "PROTECTED" : "UNPAIRED"}</strong><span>Authenticated monitor</span><span>{status?.session?.approved ? "Paired session active" : "Awaiting approval"}</span></section>
        </aside>
        <section className="dashboard-main">
            <header className="dashboard-header">
                <div><h1>Security Operations Console</h1><p>Your workspace, protected. Monitor proximity and trusted device health.</p></div>
                <div className="dashboard-actions"><span className="live-protection">● LIVE PROTECTION</span>{onShowMobile && <button className="phone-view-button" onClick={onShowMobile}>PHONE EXECUTOR</button>}<button className="unpair-button" onClick={onUnpair}>UNPAIR</button></div>
            </header>
            {error && <p className="dashboard-error">{error}</p>}
            <section className="dashboard-status-row">
                <StatusCard label="Security state" value={value(status?.state, "STARTING").toUpperCase()} tone={healthTone(status?.state === "armed")}/>
                <StatusCard label="Phone heartbeat" value={heartbeat.expired ? "EXPIRED" : "HEALTHY"} tone={healthTone(!heartbeat.expired)}/>
                <StatusCard label="Perimeter" value={perimeter.inside ? "INSIDE" : "OUTSIDE"} tone={healthTone(perimeter.inside)}/>
                <StatusCard label="Audit integrity" value={auditValid ? "VALID" : "INVALID"} tone={healthTone(auditValid)}/>
            </section>
            <section className="dashboard-monitoring-row"><ProximityGuard perimeter={perimeter}/><RelativeProximity inside={perimeter.inside === true} distance={perimeter.distance_meters}/></section>
            <section className="dashboard-details-row"><EventLog events={events}/><DecisionCard status={status}/><SystemInformation status={status}/></section>
        </section>
    </main>;
}
