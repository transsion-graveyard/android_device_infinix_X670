# Fingerprint Live Fix

## Symptom
- `vendor.fps_hal` was running, but fingerprint enroll/auth failed with `No valid device`.
- The HAL could not open its hardware module.

## Root Cause
- The live daemon tried to load `fingerprint.mt6781.so` / `fingerprint.default.so`.
- The only shipped blob was `fpsensor_fingerprint.default.so`, whose internal module id was `fpsensor_fingerprint`.
- The loader rejected it because the module id did not match `fingerprint`.

## Live Fix Applied
1. Created a temporary overlay for `/vendor/lib64/hw`.
2. Added module aliases:
   - `fingerprint.mt6781.so`
   - `fingerprint.default.so`
3. Replaced the aliases with real ELF copies of `fpsensor_fingerprint.default.so`.
4. Patched the embedded module id string from `fpsensor_fingerprint` to `fingerprint`.

## Validation
- `dumpsys fingerprint` showed the framework sensor state.
- `lshal` showed `android.hardware.biometrics.fingerprint@2.1::IBiometricsFingerprint/default`.
- Restarting `vendor.fps_hal` no longer produced the module-open failure.
- Settings fingerprint enrollment reached normal `enumerate` / `post_enroll` flow.

## Persistence Plan
- Package a real vendor module under the expected `fingerprint.mt6781.so` and `fingerprint.default.so` names.
- Keep `fpsensor_fingerprint.default.so` as the backend blob.
- Preserve existing init, VINTF, and SELinux wiring.
