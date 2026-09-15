package com.tracepulse.security;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import androidx.annotation.NonNull;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.FragmentActivity;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.Signature;
import java.util.Base64;
import java.util.UUID;

@CapacitorPlugin(name = "TracePulseNative")
public class TracePulseNativePlugin extends Plugin {
    private static final String KEY_ALIAS = "tracepulse_key";

    @PluginMethod
    public void getIdentityPublicKey(PluginCall call) {
        try {
            KeyPair pair = getOrCreateIdentity();
            JSObject result = new JSObject();
            result.put("public_key_b64", encode(rawEd25519PublicKey(pair.getPublic().getEncoded())));
            call.resolve(result);
        } catch (Exception error) {
            call.reject("identity key unavailable", error);
        }
    }

    @PluginMethod
    public void authorizeUnlock(PluginCall call) {
        if (!(getActivity() instanceof FragmentActivity)) {
            call.reject("biometric activity unavailable");
            return;
        }
        String nonce = call.getString("nonce");
        String sessionId = call.getString("sessionId");
        if (nonce == null || sessionId == null || nonce.isEmpty() || sessionId.isEmpty()) {
            call.reject("nonce and sessionId are required");
            return;
        }
        BiometricManager biometricManager = BiometricManager.from(getContext());
        int availability = biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL);
        if (availability != BiometricManager.BIOMETRIC_SUCCESS) {
            call.reject("device authentication unavailable");
            return;
        }

        long issuedAt = System.currentTimeMillis() / 1000L;
        long expiresAt = issuedAt + 30L;
        BiometricPrompt prompt = new BiometricPrompt((FragmentActivity) getActivity(), ContextCompat.getMainExecutor(getContext()), new BiometricPrompt.AuthenticationCallback() {
            @Override
            public void onAuthenticationSucceeded(@NonNull BiometricPrompt.AuthenticationResult result) {
                try {
                    KeyPair pair = getOrCreateIdentity();
                    String verificationId = UUID.randomUUID().toString();
                    String canonical = "{\"expires_at_epoch\":" + expiresAt
                            + ",\"issued_at_epoch\":" + issuedAt
                            + ",\"nonce\":" + quote(nonce)
                            + ",\"session_id\":" + quote(sessionId)
                            + ",\"verification_id\":" + quote(verificationId)
                            + ",\"version\":1}";
                    Signature signer = Signature.getInstance("Ed25519");
                    signer.initSign(pair.getPrivate());
                    signer.update(canonical.getBytes(StandardCharsets.UTF_8));
                    JSObject assertion = new JSObject();
                    assertion.put("nonce", nonce);
                    assertion.put("verification_id", verificationId);
                    assertion.put("issued_at_epoch", issuedAt);
                    assertion.put("expires_at_epoch", expiresAt);
                    assertion.put("signature_b64", encode(signer.sign()));
                    JSObject resultObject = new JSObject();
                    resultObject.put("assertion", assertion);
                    call.resolve(resultObject);
                } catch (Exception error) {
                    call.reject("unlock assertion failed", error);
                }
            }

            @Override
            public void onAuthenticationError(int errorCode, @NonNull CharSequence errString) {
                call.reject("device authentication failed: " + errString);
            }
        });
        BiometricPrompt.PromptInfo promptInfo = new BiometricPrompt.PromptInfo.Builder()
                .setTitle("TracePulse Unlock")
                .setSubtitle("Authenticate to unlock the workstation")
                .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                .build();
        prompt.authenticate(promptInfo);
    }

    private KeyPair getOrCreateIdentity() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) {
            return new KeyPair(store.getCertificate(KEY_ALIAS).getPublicKey(), (PrivateKey) store.getKey(KEY_ALIAS, null));
        }
        KeyPairGenerator generator = KeyPairGenerator.getInstance("Ed25519", "AndroidKeyStore");
        generator.initialize(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setUserAuthenticationRequired(false)
                .build());
        return generator.generateKeyPair();
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private static byte[] rawEd25519PublicKey(byte[] encoded) {
        if (encoded.length < 32) throw new IllegalArgumentException("invalid Ed25519 public key");
        byte[] raw = new byte[32];
        System.arraycopy(encoded, encoded.length - 32, raw, 0, 32);
        return raw;
    }

    private static String quote(String value) {
        return org.json.JSONObject.quote(value);
    }
}
