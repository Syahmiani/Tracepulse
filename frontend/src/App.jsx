import React, {useEffect, useMemo, useState} from "react";
import PairingScreen from "./pairing/PairingScreen";
import LaptopDashboard from "./laptop/LaptopDashboard";
import MobileDashboard from "./mobile/MobileDashboard";
import {SignedSocket} from "./security/signedSocket";

export default function App() {
    const [session, setSession] = useState(null);
    const [error, setError] = useState("");
    const [phoneMode] = useState(() => {
        const role = new URLSearchParams(location.search).get("role");
        return location.hash.includes("pairing_handle") || (role ? role === "phone" : false);
    });
    const [view, setView] = useState(() => phoneMode ? "mobile" : "laptop");
    const socket = useMemo(() => session && !session.dashboardOnly ? new SignedSocket({
        origin: session.origin,
        sessionId: session.sessionId,
        sessionKey: session.sessionKey,
        onSecurityError: exception => {
            setError(exception.message);
            if (exception.message.includes("session expired")) {
                setSession(null);
                setView("laptop");
            }
        }
    }) : null, [session]);
    const reset = () => {
        socket?.disconnect();
        setSession(null);
        setView("laptop");
        if (phoneMode) {
            localStorage.setItem("tracepulse.role", "phone");
            history.replaceState({}, "", `${location.pathname}?role=phone`);
        } else {
            localStorage.setItem("tracepulse.role", "laptop");
            history.replaceState({}, "", location.pathname);
        }
        window.location.reload();
    };

    useEffect(() => {
        const onStorage = event => {
            if (event.key === "tracepulse.reset" && event.newValue) reset();
        };
        addEventListener("storage", onStorage);
        const channel = "BroadcastChannel" in window ? new BroadcastChannel("tracepulse") : null;
        channel?.addEventListener("message", event => {
            if (event.data?.type === "unpair") reset();
        });
        return () => {
            removeEventListener("storage", onStorage);
            channel?.close();
        };
    }, [socket]);

    useEffect(() => {
        socket?.connect();
        return () => socket?.disconnect();
    }, [socket]);

    useEffect(() => {
        if (!session) return undefined;
        let stopped = false;
        const check = async () => {
            try {
                const response = await fetch(`${session.origin}/api/status`, {cache: "no-store"});
                if (!response.ok) return;
                const status = await response.json();
                if (!stopped && !status.session?.active) reset();
            } catch (exception) {
                if (!stopped) setError(exception.message || "session status unavailable");
            }
        };
        const id = setInterval(check, 1000);
        return () => {
            stopped = true;
            clearInterval(id);
        };
    }, [session]);

    if (!session) return <PairingScreen phoneMode={phoneMode} onPaired={setSession}/>;

    const unpair = async () => {
        try {
            await fetch(`${session.origin}/api/pairing/reset`, {method: "POST"});
        } finally {
            const eventId = String(Date.now());
            localStorage.setItem("tracepulse.reset", eventId);
            if ("BroadcastChannel" in window) {
                const channel = new BroadcastChannel("tracepulse");
                channel.postMessage({type: "unpair", eventId});
                channel.close();
            }
            reset();
        }
    };

    if (view === "mobile" && socket) return <>
        <nav className="view-switcher"><button onClick={() => setView("laptop")}>Laptop</button></nav>
        {error && <div className="global-error">{error}</div>}
        <MobileDashboard session={session} socket={socket} onUnpair={unpair}/>
    </>;

    return <>
        {error && <div className="global-error">{error}</div>}
        <LaptopDashboard session={session} socket={socket} onUnpair={unpair} onShowMobile={socket ? () => setView("mobile") : null}/>
    </>;
}
