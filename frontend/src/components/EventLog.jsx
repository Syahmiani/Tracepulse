const label = event => String(event || "security event").replace(/[_-]/g, " ");

function eventDetail(payload = {}) {
    if (payload.reason) return payload.reason;
    if (payload.confirmed === true) return "Action confirmed";
    if (payload.confirmed === false) return "Action was not confirmed";
    return "Authenticated security event";
}

function eventTime(timestamp) {
    return timestamp ? new Date(timestamp).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"}) : "LIVE";
}

export default function EventLog({events = []}) {
    return <section className="dashboard-card event-panel" aria-live="polite">
        <h2>Recent events</h2>
        <div className="event-list">
            {events.length === 0
                ? <p className="dashboard-empty">Waiting for authenticated security events.</p>
                : events.slice(0, 4).map((event, index) => <article className="event-row" key={`${event.nonce || event.timestamp_ms || "event"}-${index}`}>
                    <time>{eventTime(event.timestamp_ms)}</time>
                    <div><strong>{label(event.event)}</strong><span>{eventDetail(event.payload)}</span></div>
                </article>)}
        </div>
    </section>;
}
