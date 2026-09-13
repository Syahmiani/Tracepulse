export default function EventLog({events = []}) {
    return (
        <section className="panel">
            <h2>Events</h2>
            {events.length === 0 ? (
                <p className="muted">No events.</p>
            ) : (
                events.map((event, index) => (
                    <p key={index}>
                        <b>{event.event}</b> {JSON.stringify(event.payload)}
                    </p>
                ))
            )}
        </section>
    );
}