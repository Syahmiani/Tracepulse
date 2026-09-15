package com.tracepulse.security;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
	@Override
	public void onCreate(android.os.Bundle savedInstanceState) {
		registerPlugin(TracePulseNativePlugin.class);
		super.onCreate(savedInstanceState);
	}
}
