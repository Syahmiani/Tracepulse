import {ed25519,x25519} from '@noble/curves/ed25519.js';
const encoder = new TextEncoder();
const asBytes = v => v instanceof Uint8Array ? v : new Uint8Array(v);

export const base64UrlEncode = value => {
    const bytes = asBytes(value);
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

export const base64UrlDecode = value => {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const binary = atob(normalized + "=".repeat((4 - normalized.length % 4) % 4));
    return Uint8Array.from(binary, character => character.charCodeAt(0));
};

const canonicalize = value => {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === "object") {
        return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalize(value[key])]));
    }
    return value;
};
export const canonicalJson = value => JSON.stringify(canonicalize(value));

async function hmacSha256(key, value) {
    const cryptoKey = await crypto.subtle.importKey(
        "raw",
        asBytes(key),
        {name: "HMAC", hash: "SHA-256"},
        false,
        ["sign"]
    );
    return new Uint8Array(await crypto.subtle.sign(
        "HMAC",
        cryptoKey,
        typeof value === "string" ? encoder.encode(value) : asBytes(value)
    ));
}

async function hkdf(sharedSecret, info) {
    const key = await crypto.subtle.importKey("raw", asBytes(sharedSecret), "HKDF", false, ["deriveBits"]);
    return new Uint8Array(await crypto.subtle.deriveBits(
        {name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0), info: encoder.encode(info)},
        key,
        256
    ));
}

export async function createX25519KeyPair() {
    const privateKey = x25519.utils.randomPrivateKey();
    return {privateKey, publicKey: x25519.getPublicKey(privateKey)};
}

export function getBrowserIdentity() {
    const stored = localStorage.getItem("tracepulse.browser.identity");
    const privateKey = stored ? base64UrlDecode(stored) : ed25519.utils.randomSecretKey();
    if (!stored) localStorage.setItem("tracepulse.browser.identity", base64UrlEncode(privateKey));
    return {privateKey, publicKey: ed25519.getPublicKey(privateKey)};
}

export function signBrowserUnlockAssertion({privateKey, sessionId, nonce, verificationId, issuedAt, expiresAt}) {
    const message = canonicalJson({
        expires_at_epoch: expiresAt,
        issued_at_epoch: issuedAt,
        nonce,
        session_id: sessionId,
        verification_id: verificationId,
        version: 1
    });
    return base64UrlEncode(ed25519.sign(encoder.encode(message), privateKey));
}

export function deriveX25519SharedSecret(privateKey, publicKey) {
    return x25519.getSharedSecret(asBytes(privateKey), asBytes(publicKey));
}

export async function deriveSessionKey(sharedSecret, salt) {
    const key = await crypto.subtle.importKey("raw", asBytes(sharedSecret), "HKDF", false, ["deriveBits"]);
    return new Uint8Array(await crypto.subtle.deriveBits(
        {name: "HKDF", hash: "SHA-256", salt: asBytes(salt), info: encoder.encode("tracepulse/session-key/v1")},
        key,
        256
    ));
}

export async function makeClientPairingConfirmation(sharedSecret, challenge) {
    const key = await hkdf(sharedSecret, "tracepulse/pairing-confirmation/v1");
    return base64UrlEncode(await hmacSha256(key, new Uint8Array([...encoder.encode("tracepulse/client-confirmation/v1|"), ...asBytes(challenge)])));
}

export async function verifyServerPairingConfirmation(sharedSecret, challenge, confirmation) {
    const key = await hkdf(sharedSecret, "tracepulse/pairing-confirmation/v1");
    const expected = await hmacSha256(key, new Uint8Array([...encoder.encode("tracepulse/server-confirmation/v1|"), ...asBytes(challenge)]));
    const supplied = base64UrlDecode(confirmation);
    return expected.length === supplied.length && expected.every((byte, index) => byte === supplied[index]);
}

export async function signEnvelope({key, sessionId, sequence, event, payload}) {
    const unsigned = {
        version: 1,
        session_id: sessionId,
        sequence,
        timestamp_ms: Date.now(),
        nonce: base64UrlEncode(crypto.getRandomValues(new Uint8Array(16))),
        event,
        payload
    };
    return {...unsigned, hmac: base64UrlEncode(await hmacSha256(key, canonicalJson(unsigned)))};
}

export async function verifyEnvelope({key, envelope, expectedSessionId}) {
    if (envelope?.version !== 1 || envelope.session_id !== expectedSessionId) throw Error("invalid envelope");
    const {hmac, ...unsigned} = envelope;
    const expected = await hmacSha256(key, canonicalJson(unsigned));
    const supplied = base64UrlDecode(hmac);
    if (expected.length !== supplied.length || !expected.every((byte, index) => byte === supplied[index])) throw Error("invalid envelope HMAC");
    return envelope;
}

export function decodeText(value) {
    return decoder.decode(asBytes(value));
}
