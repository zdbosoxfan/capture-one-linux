# Capture One 16.6.6 on Fedora 44 with Wine

**Disclosure:** This setup, the custom color-profile proxy and the setup scripts were vibe coded with AI assistance. I make no claims about the code's efficacy, correctness, quality, or whether this is the proper way to solve the problem. These are reports from my own machine, not claims of reliability; the current limitations and provisional workarounds are described below.

**Experimental, one-workstation result — updated 2026-10-06.** RAW editing, JPEG export and menus have worked in the user's tests. The current configuration combines hardware WPF rendering, Microsoft's full-frame rendering switch and the NVIDIA EGL presentation wait described below. The user confirmed that tool drawers now close immediately and sliders and image selection work correctly. Resizing previously behaved oddly and blinked; resize, maximize/monitor behavior and sustained stability have not been validated with this latest configuration. A separate standalone WPF test still showed stale rendering, so this is not a general WPF fix. These consolidated installation steps **have not been executed end to end in a clean prefix or on a second machine**. Capture One does not officially support this Linux configuration.

**AI status and other limits:** OpenCL photo processing initializes. With the official vkd3d-proton 3.0.1 D3D12 pair, Capture One's DirectML model benchmark passed and startup selected GPU device 0 for AI acceleration. Separate FP32/FP16 ONNX tests also passed with CPU fallback disabled. An AI Subject/Background mask worked in the user test; other AI workflows and sustained AI performance remain unvalidated. The optional Open With integration is disabled. Tethering and monitor color accuracy have not been tested.

This minimal source archive contains eight files: this guide, one Wine patch, the color proxy's C/DEF files, two preparation helpers and two licenses. No binaries, application installers, fonts, accounts or user data are included. Use your own licensed Capture One installer and fonts. The procedure compiles two matching Wine modules and a compatibility DLL, installs the app, applies every setting, then launches it once.

## 1. Check the host and gather all inputs

Use this matching package baseline. Another Wine or application version requires a separate compatibility review.

| Component | Tested value |
| --- | --- |
| OS / desktop | Fedora KDE 44 x86-64; KDE 6.7.5 Wayland; XWayland 24.1.13 |
| Displays | Two 3840×2160 Dell monitors at 175%; Wine DPI 168 |
| GPU / driver | NVIDIA RTX 5090; RPM Fusion 615.71.09 |
| X11 EGL platform | NVIDIA `egl-x11` 1.0.6-1.fc44; Wine 11's default EGL backend on XWayland |
| Wine | Fedora Wine 11.0-3.fc44 staging; matching wine-core/cms and x64 wine-opencl |
| Packaged Direct3D | DXVK 2.7.1-6.fc44; its D3D9 is bypassed for the editor/helper with matching WineD3D |
| DirectML / D3D12 | Official vkd3d-proton 3.0.1 x64 D3D12 pair, app-local; existing DXVK DXGI retained |
| Application | Official CaptureOne.Win.16.6.6.3111.exe, licensed for that version |
| .NET | Windows Desktop Runtime x64 8.0.31 |
| WebView2 | x64 runtime 154.0.4258.53 |
| Other prerequisites | Winetricks corefonts, tahoma, vcrun2022; x86/x64 VC++ runtimes |
| Prefix | Dedicated 64-bit prefix; Windows 11 default; Windows 8 override only for msedgewebview2.exe |

Check the existing host before building. This guide assumes working NVIDIA/OpenCL, matching Fedora Wine core/color-management/OpenCL packages, Winetricks, cabextract, fontconfig (`fc-scan`), xdg-user-dirs and the development packages listed below. The tested NVIDIA installation included `xorg-x11-drv-nvidia-cuda` and both architectures of `xorg-x11-drv-nvidia-libs`; follow your distro's driver process if those prerequisites are missing.

The added presentation wait requires NVIDIA's X11 EGL implementation; it was validated with driver 615.71.09 and `egl-x11` 1.0.6. Its behavior is not guaranteed for other EGL vendors, GLX or native Wine Wayland. Keep this requirement separate from having a working NVIDIA/OpenCL device.

```bash
rpm -q wine wine-core wine-cms wine-opencl wine-dxvk winetricks cabextract egl-x11
/usr/bin/wine --version
nvidia-smi
```

Collect these before starting. The source ZIP contains none of these installers or fonts:

| Input | Required source/version |
| --- | --- |
| Capture One installer | Your official `CaptureOne.Win.16.6.6.3111.exe` and a license covering that version |
| .NET Desktop Runtime | [Microsoft x64 8.0.31 installer](https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/8.0.31/windowsdesktop-runtime-8.0.31-win-x64.exe) |
| WebView2 runtime | [Microsoft x64 Evergreen Standalone](https://go.microsoft.com/fwlink/p/?LinkId=2124701); tested runtime 154.0.4258.53 |
| D3D12 compatibility | [Official vkd3d-proton 3.0.1 archive](https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v3.0.1/vkd3d-proton-3.0.1.tar.zst); save as `vkd3d-proton-3.0.1.tar.zst` in Downloads |
| UI fonts | Eight files from a source you are licensed to use, listed in the preflight below |
| Wine source RPM | [Fedora wine-11.0-3.fc44.src.rpm](https://ftp-osl.osuosl.org/pub/fedora/linux/releases/44/Everything/source/tree/Packages/w/wine-11.0-3.fc44.src.rpm); save as `wine-11.0-3.fc44.src.rpm` in Downloads; verify in Step 2 |

Dual boot and a Windows partition are not required. A Windows drive was used during investigation and font sourcing, but you can stage the eight listed Microsoft font files in any ordinary Linux directory and point `C1_FONTS_SOURCE` there. The recipe still requires those fonts from a source licensed for your intended use; no font-free alternative has been tested.

The WebView2 link tracks newer releases, so record its actual version. A different downloaded runtime has not been validated by this recipe. The tested WebView2 installer was 212,272,848 bytes, SHA-256 `f6df8e4bc857786ff641cd01da1449169eaf8236c936ced485ea61685ba4da40`, and installed runtime 154.0.4258.53 (wrapper version 1.3.271.7).

The versioned .NET installer SHA-512 was verified against [Microsoft metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/8.0/releases.json):

```text
605189223cf0a64bfb5453520b794d1d386a97c7e65e3944feaf9214db1a8b247f66c569265aef4204447baf5b5ff19559c323d887e1318f17deb28a5af0fa12
```

Make these development packages available in a Fedora 44 build environment, letting its package manager resolve dependencies such as HarfBuzz, PNG, zlib and Brotli:

```text
gcc make autoconf bison flex perl python3 patch diffutils tar gzip xz zstd
rpm rpm-build cpio pkgconf-pkg-config mingw64-gcc mingw64-headers mingw64-crt
libX11-devel libXcomposite-devel libXcursor-devel libXrender-devel
libXrandr-devel libXinerama-devel libXi-devel libXext-devel libXfixes-devel
libXxf86vm-devel libglvnd-devel xorg-x11-proto-devel
vulkan-loader-devel vulkan-headers freetype-devel fontconfig-devel
```

The original build used privately extracted signed RPM headers/libraries; using standard development packages is a simpler reconstruction, not a separately tested build environment. Only two Unix modules are rebuilt; other modules are copied from matching installed Wine.

Open a Bash terminal **in the extracted kit directory**. Set your font location and preferred Wine DPI below. DPI 168 reproduces the tested 175% scale; use 96 for 100% or 144 for 150%. This is prefix scaling, not a resize fix.

These commands expect a **new build directory, prefix and runner**. Keep an existing installation separate; do not run this fresh-install procedure over it.

```bash
set -euo pipefail
export C1_KIT="$(pwd)"
export C1_BUILD="$HOME/capture-one-wine-build"
export C1_FILES="$C1_BUILD/out"
export C1_RUNNER="$HOME/.local/share/capture-one/runners/wine11-valve-ulw"
export WINEPREFIX="$HOME/.local/share/capture-one/prefix-wine11"
export C1_APP="$WINEPREFIX/drive_c/Program Files/Capture One/Capture One"
export C1_DOWNLOADS="$HOME/Downloads"
export C1_FONTS_SOURCE='/path/to/your/licensed-fonts'
export C1_DPI=168
for C1_SOURCE in README.md capture-one-wine11-fedora.patch mscms-compat.c mscms.def \
  clone-private-runner.py prepare-private-wine-dlls.py LICENSE-MIT.txt LICENSE-LGPL-2.1.txt; do
  test -f "$C1_KIT/$C1_SOURCE"
done
sha256sum --check <<'C1_PATCH_HASH'
9413b48fdac58816e036c3299c2d8472325db628b801564cb8a87ad1eeed1681  capture-one-wine11-fedora.patch
C1_PATCH_HASH
test "$(rpm -q --qf '%{VERSION}-%{RELEASE}' wine-core.x86_64)" = '11.0-3.fc44'
for C1_NEW_PATH in "$C1_BUILD" "$WINEPREFIX" "$C1_RUNNER"; do
  test ! -e "$C1_NEW_PATH"
  test ! -L "$C1_NEW_PATH"
done
for C1_FILE in CaptureOne.Win.16.6.6.3111.exe \
  windowsdesktop-runtime-8.0.31-win-x64.exe MicrosoftEdgeWebView2RuntimeInstallerX64.exe \
  wine-11.0-3.fc44.src.rpm vkd3d-proton-3.0.1.tar.zst; do
  test -f "$C1_DOWNLOADS/$C1_FILE"
done
for C1_FONT in segoeui.ttf segoeuib.ttf segoeuii.ttf segoeuiz.ttf \
  seguisb.ttf seguisym.ttf segmdl2.ttf SegoeIcons.ttf; do
  test -f "$C1_FONTS_SOURCE/$C1_FONT"
done
test -n "${DISPLAY:-}" || { echo 'Use a terminal in your graphical desktop.' >&2; exit 1; }
```

Stop at a failed check and resolve that input. The commands use the chosen paths throughout; do not restart from Step 1 after creating the prefix.

## 2. Build the private runner and compatibility files

### Prepare the exact Fedora source

Confirm that the internal loader, ntdll and wineserver belong to the same installed Fedora Wine **11.0-3.fc44** build. Do not substitute Wine 11.18, Proton or another Fedora revision. Keep this stock installation unchanged through the installation phase.

```bash
rpm -qf /usr/lib64/wine-wow64/wine/x86_64-unix/wine \
  /usr/lib64/wine-wow64/wine/x86_64-unix/ntdll.so /usr/bin/wineserver64
mkdir -p "$C1_BUILD/srpm" "$C1_BUILD/source" "$C1_BUILD/build" "$C1_FILES"
cp "$C1_DOWNLOADS/wine-11.0-3.fc44.src.rpm" "$C1_BUILD/"
```

The source must have a trusted Fedora signature, not just a digest or `NOKEY`. Verify the signature and exact archive hash before extracting:

```bash
rpmkeys --checksig "$C1_BUILD/wine-11.0-3.fc44.src.rpm"
(cd "$C1_BUILD" && sha256sum --check <<'C1_RPM_HASH'
c4c777b791171cdfb34cefd787c1dba4a78791ce4dddfff0e78574e442ef4045  wine-11.0-3.fc44.src.rpm
C1_RPM_HASH
)
```

Extract only after verifying it. These commands assume empty work directories:

```bash
cd "$C1_BUILD/srpm"
rpm2cpio ../wine-11.0-3.fc44.src.rpm | cpio -id --no-absolute-filenames
cd "$C1_BUILD/source"
tar -xf ../srpm/wine-11.0.tar.xz
cd wine-11.0
patch --batch --fuzz=0 -p1 -i "$C1_BUILD/srpm/wine-cjk.patch"
tar -xf "$C1_BUILD/srpm/wine-staging-11.0.tar.gz" --strip-components=1
python3 staging/patchinstall.py DESTDIR="$PWD" --all -W server-Stored_ACLs
autoreconf -f
./tools/make_requests
```

This follows the packaged `wine.spec` staging selection. Do not apply staging
twice. Stop on a source or hash mismatch; do not substitute a similar release.
Apply the combined patch: both published Valve changes plus the local NVIDIA EGL wait integration:

```bash
sha256sum --check <<'C1_SOURCE_BEFORE'
82ff003a03691a3a25312597faa8e2715def2a05ac203faf43d7b07edcf03fd1  dlls/win32u/dce.c
da80eb20f86d362beac08a8af59367d7b218c2719a93e14a3f2061b9ed4fea99  dlls/win32u/window.c
ce7f660783820716ce2c145ff2cd04ce6b385169fe626e1e7b47ae675fea6c55  dlls/winex11.drv/init.c
edcd9e9ef34d519f2649d861a2fe9d956a2dc3f969ceebf5ca9f94129040650c  dlls/winex11.drv/opengl.c
bb800643ecea564a364869fa904930ce6d02aadfc2a0ea99874de03689cbd39d  include/wine/gdi_driver.h
C1_SOURCE_BEFORE
patch --batch --fuzz=0 --dry-run -p1 \
  -i "$C1_KIT/capture-one-wine11-fedora.patch"
patch --batch --fuzz=0 -p1 \
  -i "$C1_KIT/capture-one-wine11-fedora.patch"
sha256sum --check <<'C1_SOURCE_AFTER'
cfd5469c9c38741a086df2c10430c14f7102a5524fe64355676710ea9b125d08  dlls/win32u/dce.c
5f38c33ac9736f01c2c535773b0b546165d4bc0f3aa23e559b2d272ac746f605  dlls/win32u/window.c
68734213a61e62f3c4a0f703e606d514473506d2c321b023f49f0f1ddda5d44c  dlls/winex11.drv/init.c
1f75b6167c7b353fffc22b6f6b3ac4faff3aabec91234f99ac5d24840e2cf002  dlls/winex11.drv/opengl.c
665b13ca6f4b9e62c84437ad05da10fe716b6008153fc2422716c54d246ba147  include/wine/gdi_driver.h
C1_SOURCE_AFTER
```

The original pair comes from Valve commits
[`1dc8060`](https://github.com/ValveSoftware/wine/commit/1dc8060af449d69cc4e8240732019224aab290b7)
and
[`d8a27b4`](https://github.com/ValveSoftware/wine/commit/d8a27b4712eaeb54f0a69e6dc98d39055a811ce2).
Wine 11 lacks Proton's initial fullscreen/offscreen logic, so this backport
initializes `needs_offscreen` to `FALSE` before the published alpha-mask block.
The additional `opengl.c` change calls `eglWaitGL` before copying an offscreen
EGL presentation, only after a successful swap with a current context and a
matching current draw surface. It uses NVIDIA engineer Kyle Brenneman's
[existing Present-completion wait](https://github.com/NVIDIA/egl-x11/commit/73680e02218a031202faff79de3e7d683428d2dd),
present in [egl-x11 1.0.6](https://github.com/NVIDIA/egl-x11/tree/v1.0.6).
This Wine call site is a **local integration, not an accepted upstream Wine
patch**. It relies on NVIDIA/GLVND behavior rather than a portable guarantee
for desktop OpenGL. The wait can block for presentation completion; the
passing embedded-WPF tests and Capture One user test do not establish safety
or performance for every window lifecycle or another driver.
The combined five-file patch passed a zero-fuzz dry-run and reproduced the
reviewed build-source hashes; that does not replace a clean installation test.

### Build both Unix modules with font support

The following explicit flags reproduce the sanitized Fedora `wine.spec`
compiler/linker choices used in the successful local build. The original
private sysroot added its `-I` and `-L` paths. With system development packages
in the build environment, omit those private paths:

```bash
unset PKG_CONFIG_PATH PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR
export CFLAGS='-fexceptions -g -grecord-gcc-switches -pipe -Wall -Wno-complain-wrong-lang -Werror=format-security -Wp,-D_GLIBCXX_ASSERTIONS -m64 -march=x86-64 -mtune=generic -fasynchronous-unwind-tables -mtls-dialect=gnu2 -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer -O2'
export LDFLAGS='-Wl,--as-needed -Wl,-z,pack-relative-relocs'
cd "$C1_BUILD/build"
"$C1_BUILD/source/wine-11.0/configure" \
  --prefix=/usr --libdir=/usr/lib64/wine-wow64 --sysconfdir=/etc/wine \
  --enable-win64 --enable-archs=x86_64 --disable-tests \
  --with-x --with-freetype --with-fontconfig --with-opengl --with-vulkan
```

Check required font/graphics features before compiling:

```bash
python3 - <<'PY'
from pathlib import Path
import re
config = Path('include/config.h').read_text()
required = 'HAVE_FT2BUILD_H SONAME_LIBFREETYPE SONAME_LIBFONTCONFIG SONAME_LIBGL SONAME_LIBEGL SONAME_LIBVULKAN SONAME_LIBX11 SONAME_LIBXEXT SONAME_LIBXCOMPOSITE SONAME_LIBXCURSOR SONAME_LIBXFIXES SONAME_LIBXI SONAME_LIBXINERAMA SONAME_LIBXRANDR SONAME_LIBXRENDER SONAME_LIBXXF86VM'.split()
missing = [name for name in required
           if not re.search(r'^#define\s+' + re.escape(name) + r'\s+', config, re.M)]
assert not missing, 'Missing Wine build features: ' + ', '.join(missing)
PY
```

Do not reuse an X11-only build configured with `--without-freetype` or
`--without-fontconfig`. That would remove working font support from win32u.
Unrelated missing sound/USB/network build dependencies are acceptable only
because those modules are not built or installed by this recipe.

```bash
mkdir -p dlls/ntdll
cp /usr/lib64/wine-wow64/wine/x86_64-unix/ntdll.so dlls/ntdll/ntdll.so
sha256sum dlls/ntdll/ntdll.so \
  /usr/lib64/wine-wow64/wine/x86_64-unix/ntdll.so
make -j16 -o dlls/ntdll/ntdll.so \
  dlls/win32u/win32u.so dlls/winex11.drv/winex11.so
cp dlls/win32u/win32u.so "$C1_FILES/win32u.valve-ulw.so"
cp dlls/winex11.drv/winex11.so "$C1_FILES/winex11.valve-ulw.so"
```

`make -o` retains the copied stock ntdll link input. Do not run `make install`.
If copying the stock module from a host into a container, match the source
version, CPU architecture and compatible host libraries; the resulting
artifacts are intended for that same host runtime.

The build preserves required font/graphics features and the original exports, adding `window_surface_get` to win32u. It is not a byte-for-byte reproduction of the distribution binaries.

For provenance, the tested local `winex11.so` was SHA-256 `6bd4521183e60ad41bd6d603cd5138ab0a68758abdd0e463ec8f8b25ea39881d`; `win32u.so` retained the original two-commit build. A different build environment may produce a different binary digest even with the five source hashes above matching.

### Make a frozen private Wine runner

Use a **new** destination. The included helper copies the complete installed
Wine core, PE companions, Wine data and wineserver, preserves internal relative
links, freezes alternatives/external file links to private copies, and records
hashes. It never opens a Wine prefix. It refuses an existing destination.

```bash
python3 "$C1_KIT/clone-private-runner.py" "$C1_RUNNER"
```

The helper implements the equivalent of copying these trees/files, with
additional private symlink resolution and hash checks:

```text
/usr/lib64/wine-wow64/wine  -> RUNNER/lib64/wine-wow64/wine
/usr/share/wine            -> RUNNER/share/wine
/usr/bin/wineserver64      -> RUNNER/bin/wineserver
```

Wine-dependent files must be real private copies so a future system update
does not mix Wine versions. Ordinary ELF libraries such as glibc, OpenGL and
X11 still come from the host. Existing prefix registrations may retain absolute
Mono/Gecko/font paths; the helper does not rewrite them or make a self-contained
cross-distro runtime.

The actual entry point is the **internal loader**, adjacent to the privately
copied `ntdll.so`. `/usr/bin/wine64` is a launcher shim on this Fedora package.
A `WINEDLLPATH` override alone does not provide the same isolation.

Before using the new runner, preserve its unpatched pair and overlay both:

```bash
mkdir "$C1_RUNNER/original-modules"
cp "$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/win32u.so" \
  "$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/winex11.so" \
  "$C1_RUNNER/original-modules/"
cp "$C1_FILES/win32u.valve-ulw.so" \
  "$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/win32u.so"
cp "$C1_FILES/winex11.valve-ulw.so" \
  "$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/winex11.so"
"$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/wine" --version
"$C1_RUNNER/bin/wineserver" --version
```

The X11 module imports the new `window_surface_get` ELF symbol. Never combine
the patched X11 module with unpatched win32u. Matching PE companions remain
from the copied Fedora runtime; this patch does not change their interfaces.

### Build and prepare the three application-local DLLs

With the matching x86-64 MinGW compiler available:

```bash
cd "$C1_FILES"
x86_64-w64-mingw32-gcc -O2 -Wall -Wextra \
  -Wno-cast-function-type -Wno-multichar -static-libgcc -shared \
  "$C1_KIT/mscms-compat.c" "$C1_KIT/mscms.def" \
  -o mscms.dll
```

The proxy forwards to an adjacent private copy named `mscms_wine.dll`.
The OpenGL rendering configuration also needs the matching **WineD3D**
`wine-d3d9.dll`, rather than Fedora's alternatives-selected DXVK `d3d9.dll`.
The preparation helper below copies these two Wine files from the private
runner into the output directory and changes their Wine builtin DOS marker
so native app-local loading is possible. It verifies the known source and
output hashes and refuses overwrites; it does not modify executable code or
any installed file:

```bash
python3 "$C1_KIT/prepare-private-wine-dlls.py" "$C1_RUNNER" "$C1_FILES"
```

### Prepare the official D3D12 pair for DirectML

The tested DXVK DXGI and Wine builtin D3D12 combination failed to initialize DirectML. The official vkd3d-proton pair corrected device initialization, passed isolated FP32/FP16 GPU computation, and passed Capture One's startup model benchmark. [Upstream documents using both native D3D12 DLLs with DXVK DXGI](https://github.com/HansKristian-Work/vkd3d-proton/blob/v3.0.1/README.md#using-vkd3d-proton). This step retains the existing DXGI and WineD3D9; hardware WPF with full-frame rendering and photo OpenCL are configured below.

Verify the exact [3.0.1 release](https://github.com/HansKristian-Work/vkd3d-proton/releases/tag/v3.0.1), then extract only its two x64 DLLs into the build output. The archive digest was checked against the release asset's published SHA-256. These binaries are downloaded separately and are not included in this source kit. No upstream installation script is run.

```bash
(cd "$C1_DOWNLOADS" && sha256sum --check <<'C1_VKD3D_ARCHIVE'
3cf2315522af5e43605ef6d3c41dad91387040bf97199934f3f7ab76caaa2f0c  vkd3d-proton-3.0.1.tar.zst
C1_VKD3D_ARCHIVE
)
for C1_DLL in d3d12.dll d3d12core.dll; do
  test ! -e "$C1_FILES/$C1_DLL"
  test ! -L "$C1_FILES/$C1_DLL"
done
tar --zstd --extract --file "$C1_DOWNLOADS/vkd3d-proton-3.0.1.tar.zst" \
  --directory "$C1_FILES" --strip-components=2 \
  --no-same-owner --no-same-permissions --keep-old-files -- \
  vkd3d-proton-3.0.1/x64/d3d12.dll \
  vkd3d-proton-3.0.1/x64/d3d12core.dll
(cd "$C1_FILES" && sha256sum --check <<'C1_VKD3D_FILES'
aed51497c0efa76c9ffc30386ff0957197824cd4734ce64b4e962d3551fba43c  d3d12.dll
68b8bc7b32f9b1b1b0526e9e2e769731dd8da9af0f2b40f76012385b9d5721df  d3d12core.dll
C1_VKD3D_FILES
)
```

The build is complete. No application prefix or launch was needed. Clear compiler flags and select matching stock Fedora Wine for installation/configuration:

```bash
cd "$C1_KIT"
unset CFLAGS CPPFLAGS LDFLAGS PKG_CONFIG_PATH PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR
unset WINELOADER WINEDLLPATH WINEDLLOVERRIDES WINESERVER WINE
unset WAYLAND_DISPLAY
export WINEARCH=win64
export WINEDEBUG=-all
export WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--disable-gpu
export WINE_D3D_CONFIG=renderer=gl
for C1_FILE in mscms.dll mscms_wine.dll d3d9.dll d3d12.dll d3d12core.dll; do
  test -f "$C1_FILES/$C1_FILE"
done
test -x "$C1_RUNNER/lib64/wine-wow64/wine/x86_64-unix/wine"
test -x "$C1_RUNNER/bin/wineserver"
```

Recheck the stock runtime after building, particularly if the package manager updated Wine in the meantime. All three file owners must still report 11.0-3.fc44; stop on a mismatch:

```bash
test "$(rpm -q --qf '%{VERSION}-%{RELEASE}' wine-core.x86_64)" = '11.0-3.fc44'
for C1_RUNTIME in /usr/lib64/wine-wow64/wine/x86_64-unix/wine \
  /usr/lib64/wine-wow64/wine/x86_64-unix/ntdll.so /usr/bin/wineserver64; do
  test "$(rpm -qf --qf '%{VERSION}-%{RELEASE}' "$C1_RUNTIME")" = '11.0-3.fc44'
done
```

Keep the stock runner for all `/usr/bin/wine` commands below. There is one transition to the private runner in Step 5; do not alternate runners while the prefix is active.

## 3. Install prerequisites and Capture One; keep the editor closed

Initialize the dedicated prefix and install its prerequisites:

```bash
test ! -e "$WINEPREFIX"
test ! -L "$WINEPREFIX"
mkdir -p "$WINEPREFIX"
chmod 700 "$WINEPREFIX"
/usr/bin/wineboot -u
/usr/bin/wine winecfg -v win11
WINE=/usr/bin/wine winetricks -q corefonts tahoma vcrun2022
/usr/bin/wine "$C1_DOWNLOADS/windowsdesktop-runtime-8.0.31-win-x64.exe" \
  /install /quiet /norestart
/usr/bin/wine "$WINEPREFIX/drive_c/Program Files/dotnet/dotnet.exe" --list-runtimes
/usr/bin/wine "$C1_DOWNLOADS/MicrosoftEdgeWebView2RuntimeInstallerX64.exe" /silent /install
```

Confirm the runtime listing contains **Microsoft.NETCore.App 8.0.31** and **Microsoft.WindowsDesktop.App 8.0.31**. Wine Mono or .NET Framework 4.x is not a substitute for this Desktop Runtime. Check the actual WebView2 runtime directory, rather than the installer's wrapper version:

```bash
python3 - <<'PY'
from pathlib import Path
import os
root = Path(os.environ['WINEPREFIX']) / 'drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application'
versions = sorted(p.name for p in root.iterdir() if (p / 'msedgewebview2.exe').is_file())
print('Installed WebView2 runtimes:', ', '.join(versions))
assert versions == ['154.0.4258.53'], 'Expected only the tested WebView2 runtime; review missing, different or coexisting versions before continuing.'
PY
```

The Evergreen URL may provide a newer version; the check requires the tested runtime alone and stops if any other version is also installed.

Install Capture One using the recorded silent installer flags:

```bash
/usr/bin/wine "$C1_DOWNLOADS/CaptureOne.Win.16.6.6.3111.exe" \
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
test -f "$C1_APP/CaptureOne.exe"
```

Repeat the WebView2 directory check above after installing Capture One, before continuing. An installer may change the available runtimes; continue only when the tested version remains the sole installed runtime.

**Do not launch or sign in yet.** If an installer opens the editor automatically, close it before Step 4. Leave the application's files unused while applying the final configuration.

## 4. Apply the complete configuration before first launch

### Application-local compatibility DLLs

Copy the color-profile proxy, its matching Wine implementation, matching WineD3D9, and the verified official D3D12 pair together. The guard refuses replacements:

```bash
for C1_DLL in mscms.dll mscms_wine.dll d3d9.dll d3d12.dll d3d12core.dll; do
  test ! -e "$C1_APP/$C1_DLL"
  test ! -L "$C1_APP/$C1_DLL"
done
cp "$C1_FILES/mscms.dll" "$C1_FILES/mscms_wine.dll" \
  "$C1_FILES/d3d9.dll" "$C1_FILES/d3d12.dll" \
  "$C1_FILES/d3d12core.dll" "$C1_APP/"
```

### Fonts

Register the eight preflighted fonts in this prefix. The script checks font identity and refuses conflicts. No host fonts are replaced.

```bash
python3 - "$C1_FONTS_SOURCE" <<'PY'
from pathlib import Path
import hashlib, os, shutil, subprocess, sys
source = Path(sys.argv[1])
target = Path(os.environ['WINEPREFIX']) / 'drive_c/windows/Fonts'
fonts = {
    'segoeui.ttf': 'Segoe UI',
    'segoeuib.ttf': 'Segoe UI Bold',
    'segoeuii.ttf': 'Segoe UI Italic',
    'segoeuiz.ttf': 'Segoe UI Bold Italic',
    'seguisb.ttf': 'Segoe UI Semibold',
    'seguisym.ttf': 'Segoe UI Symbol',
    'segmdl2.ttf': 'Segoe MDL2 Assets',
    'SegoeIcons.ttf': 'Segoe Fluent Icons',
}
assert target.is_dir() and not target.is_symlink()
for filename, family in fonts.items():
    src, dst = source / filename, target / filename
    assert src.is_file() and not src.is_symlink(), filename
    assert not dst.exists() and not dst.is_symlink(), 'Existing target: ' + filename
    identity = subprocess.check_output(
        ['fc-scan', '--format', '%{fullname}', str(src)], text=True).split(',')[0]
    assert identity == family, 'Unexpected font identity: ' + filename
key = r'HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
for filename, family in fonts.items():
    src, dst = source / filename, target / filename
    with src.open('rb') as original, dst.open('xb') as copied:
        shutil.copyfileobj(original, copied)
    dst.chmod(0o644)
    assert hashlib.sha256(src.read_bytes()).digest() == hashlib.sha256(dst.read_bytes()).digest()
    subprocess.run(['/usr/bin/wine', 'reg', 'add', key, '/v', family + ' (TrueType)',
                    '/t', 'REG_SZ', '/d', filename, '/f'], check=True)
print('Eight prefix-only fonts installed; continue configuration before launching Capture One.')
PY
```

### Prefix and application settings

Apply the current local configuration together: Windows 11 for the prefix, Windows 8 only for the embedded browser, editor-scoped color and D3D12 overrides, WineD3D9 for both editor and helper, hardware WPF, OpenCL photo processing and the selected DPI. Then merge the full-frame WPF switch into both runtime configurations below, before any application launch. The D3D12 overrides affect only `CaptureOne.exe`; the existing DXGI configuration is retained.

```bash
/usr/bin/wine winecfg -v win11
/usr/bin/wine reg add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe' \
  /v Version /t REG_SZ /d win8 /f
for C1_DLL in mscms mscms_wine d3d12 d3d12core; do
  /usr/bin/wine reg add 'HKCU\Software\Wine\AppDefaults\CaptureOne.exe\DllOverrides' \
    /v "$C1_DLL" /t REG_SZ /d native /f
done
for C1_EXE in CaptureOne.exe P1.WebView.exe; do
  /usr/bin/wine reg add 'HKCU\Software\Wine\AppDefaults\'"$C1_EXE"'\DllOverrides' \
    /v d3d9 /t REG_SZ /d native /f
done
/usr/bin/wine reg add 'HKCU\Software\Microsoft\Avalon.Graphics' \
  /v DisableHWAcceleration /t REG_DWORD /d 0 /f
/usr/bin/wine reg add 'HKCU\Software\Phase One\Capture One' \
  /v UseOpenCL /t REG_DWORD /d 1 /f
/usr/bin/wine reg add 'HKCU\Control Panel\Desktop' \
  /v LogPixels /t REG_DWORD /d "$C1_DPI" /f
```

Merge Microsoft's existing `Switch.System.Windows.Media.MediaContext.DisableDirtyRectangles` property into **both** `CaptureOne.runtimeconfig.json` and `P1.WebView.runtimeconfig.json`. It requests full-frame WPF rendering and presentation. The installed .NET Desktop Runtime 8.0.31 contains this switch. [Microsoft's WPF change](https://github.com/dotnet/wpf/pull/5837) and [issue discussion](https://github.com/dotnet/wpf/issues/5441) document its purpose. The following block backs up both original files before writing, preserves the remaining JSON settings, and refuses an existing backup or property:

```bash
python3 - <<'PY'
from pathlib import Path
import json, os, shutil
app = Path(os.environ['C1_APP'])
prefix = Path(os.environ['WINEPREFIX'])
backup = Path(os.environ['C1_BUILD']) / 'runtimeconfig-before-full-frame'
switch = 'Switch.System.Windows.Media.MediaContext.DisableDirtyRectangles'
names = ['CaptureOne.runtimeconfig.json', 'P1.WebView.runtimeconfig.json']
assert not backup.exists() and not backup.is_symlink(), 'Preserve existing runtimeconfig backups.'
runtime = prefix / 'drive_c/Program Files/dotnet/shared/Microsoft.WindowsDesktop.App/8.0.31/PresentationCore.dll'
assert switch.encode('utf-16le') in runtime.read_bytes(), 'Required WPF switch missing from the expected runtime.'
plans = []
for name in names:
    path = app / name
    temp = path.with_name(name + '.full-frame-new')
    assert path.is_file() and not path.is_symlink()
    assert not temp.exists() and not temp.is_symlink()
    original = path.read_bytes()
    data = json.loads(original.decode('utf-8-sig'))
    properties = data['runtimeOptions'].setdefault('configProperties', {})
    assert isinstance(properties, dict) and switch not in properties, 'Review existing switch: ' + name
    properties[switch] = True
    plans.append((path, temp, original, (json.dumps(data, indent=2) + '\n').encode('utf-8')))
backup.mkdir(mode=0o700)
for path, temp, original, updated in plans:
    assert path.read_bytes() == original, 'Configuration changed during preparation.'
    shutil.copy2(path, backup / path.name)
for path, temp, original, updated in plans:
    assert path.read_bytes() == original, 'Configuration changed during preparation.'
    with temp.open('xb') as f:
        f.write(updated)
    temp.chmod(path.stat().st_mode & 0o777)
    os.replace(temp, path)
    assert json.loads(path.read_text())['runtimeOptions']['configProperties'][switch] is True
print('Full-frame WPF enabled in both configurations; originals:', backup)
PY
```

The latest user test confirmed responsive sliders and correct image selection with this combination. The NVIDIA EGL wait built in Step 2 additionally fixed tool drawers waiting for mouse movement before closing. Photo OpenCL and DirectML remain configured separately. App updates may replace the runtime configuration files; inspect and reapply only this property after reviewing the new runtime, rather than replacing updated files with old copies.

### Disable the failing optional Open With integration

The tested configuration disables this plugin to avoid its initialization popup. Apply this once before launch; ordinary editing/export remains available. Keep the renamed manifest for rollback:

```bash
test ! -e "$C1_APP/Plugins/OpenWith/manifest.xml.disabled-for-wine"
test ! -L "$C1_APP/Plugins/OpenWith/manifest.xml.disabled-for-wine"
mv "$C1_APP/Plugins/OpenWith/manifest.xml" \
   "$C1_APP/Plugins/OpenWith/manifest.xml.disabled-for-wine"
```

## 5. Check installed files, create shortcuts and switch runners once

Check the installed DLLs match the prepared files:

```bash
for C1_DLL in mscms.dll mscms_wine.dll d3d9.dll d3d12.dll d3d12core.dll; do
  cmp "$C1_FILES/$C1_DLL" "$C1_APP/$C1_DLL"
done
```

Create the final wrapper and shortcuts. This inline launcher substitutes your paths and refuses existing files. It does not launch the app:

```bash
python3 - <<'PY'
from pathlib import Path
import os, shlex, subprocess
prefix = os.environ['WINEPREFIX']
runner = os.environ['C1_RUNNER']
wrapper = Path.home() / '.local/bin/capture-one-wine'
menu = Path.home() / '.local/share/applications/capture-one-wine.desktop'
desktop_dir = Path(subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip())
assert desktop_dir.is_absolute()
desktop = desktop_dir / 'Capture One.desktop'
for path in [wrapper, menu, desktop]:
    assert not path.exists() and not path.is_symlink(), 'Back up existing target: ' + str(path)
source = r'''#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Adapt prefix and runner paths before use; requires the guide's app-local DLLs and registry settings.
set -euo pipefail
# Matching Fedora Wine 11 with CodeWeavers/Valve ULW fixes and the local NVIDIA EGL wait.
export WINEPREFIX="$HOME/.local/share/capture-one/prefix-wine11"
c1_runner="$HOME/.local/share/capture-one/runners/wine11-valve-ulw"
export WINESERVER="$c1_runner/bin/wineserver"
unset WINELOADER WINEDLLPATH WINEDLLOVERRIDES WINEARCH
export WINEDEBUG=-all
export WINE_D3D_CONFIG=renderer=gl
# Embedded browser rendering only; photo OpenCL is configured separately.
export WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--disable-gpu
# This configuration requires NVIDIA X11 EGL, including XWayland on the Plasma desktop.
unset WAYLAND_DISPLAY
if [[ -z "${DISPLAY:-}" ]]; then
    printf '%s\n' 'Capture One requires the desktop XWayland display.' >&2
    exit 1
fi
app_dir="$WINEPREFIX/drive_c/Program Files/Capture One/Capture One"
cd "$app_dir"
# Wine-created file and protocol associations must use this same private runner.
if [[ "${1:-}" == --wine-start ]]; then
    shift
    exec "$c1_runner/lib64/wine-wow64/wine/x86_64-unix/wine" start.exe "$@"
fi
exec "$c1_runner/lib64/wine-wow64/wine/x86_64-unix/wine" "$app_dir/CaptureOne.exe" "$@"
'''
source = source.replace('export WINEPREFIX="$HOME/.local/share/capture-one/prefix-wine11"',
                        'export WINEPREFIX=' + shlex.quote(prefix))
source = source.replace('c1_runner="$HOME/.local/share/capture-one/runners/wine11-valve-ulw"',
                        'c1_runner=' + shlex.quote(runner))
wrapper.parent.mkdir(parents=True, exist_ok=True)
with wrapper.open('x') as f:
    f.write(source)
wrapper.chmod(0o755)
arg = str(wrapper).replace('%', '%%')
arg = ''.join(('\\' + c) if c in '\\"`$' else c for c in arg)
quoted_exec = ('"' + arg + '"').replace('\\', '\\\\')
entry = ('[Desktop Entry]\nType=Application\nName=Capture One (Wine)\n'
         'Comment=Capture One through a private Wine runner\n'
         'Exec=' + quoted_exec + '\nIcon=applications-graphics\n'
         'Terminal=false\nCategories=Graphics;Photography;\n'
         'StartupNotify=true\nStartupWMClass=captureone.exe\n')
for path in [menu, desktop]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(entry)
    path.chmod(0o755 if path == desktop else 0o644)
print('Created launcher, application-menu entry and Desktop shortcut.')
PY
```

Route Wine's Capture One file and sign-in protocol handlers through that wrapper too. Otherwise opening a catalog or a `captureone:` link can bypass its private runner and graphics environment. The step below only rewrites Wine-generated file/protocol entries named exactly `CaptureOne` whose original command names this prefix. It preserves their ProgID and `%f`/`%u` arguments, leaves generic Wine associations and other prefixes alone, and backs up every matched entry before writing. No MIME default is changed. Rerun this check if reinstalling the application regenerates its handlers.

```bash
python3 - <<'PY'
from pathlib import Path
import os, re, shutil, tempfile
apps = Path.home() / '.local/share/applications'
wrapper = Path.home() / '.local/bin/capture-one-wine'
assert wrapper.is_file()
old_prefix = 'Exec=env "WINEPREFIX=' + os.environ['WINEPREFIX'] + '" wine start '
arg = str(wrapper).replace('%', '%%')
arg = ''.join(('\\' + c) if c in '\\"`$' else c for c in arg)
new_prefix = 'Exec=' + ('"' + arg + '"').replace('\\', '\\\\') + ' --wine-start '
changes = []
for path in sorted(apps.glob('wine-*.desktop')):
    if not (path.name.startswith('wine-extension-') or
            path.name == 'wine-protocol-captureone.desktop'):
        continue
    if path.is_symlink():
        continue
    before = path.read_bytes()
    text = before.decode('utf-8')
    lines = text.splitlines()
    if 'Name=CaptureOne' not in lines:
        continue
    commands = [line for line in lines if line.startswith('Exec=')]
    assert len(commands) == 1, 'Review unexpected Exec fields: ' + str(path)
    if not commands[0].startswith(old_prefix):
        continue
    args = commands[0][len(old_prefix):]
    if path.name == 'wine-protocol-captureone.desktop':
        assert args == '%u', 'Review protocol arguments: ' + str(path)
    else:
        assert re.fullmatch(r'/ProgIDOpen "CaptureOne[A-Za-z0-9]+" %f', args), path
    after = text.replace(commands[0], new_prefix + args, 1).encode('utf-8')
    changes.append((path, before, after))
if changes:
    backup = Path(tempfile.mkdtemp(prefix='association-backups-',
                                   dir=os.environ['C1_BUILD']))
    for path, before, after in changes:
        assert path.read_bytes() == before, 'Entry changed during review: ' + str(path)
        shutil.copy2(path, backup / path.name)
    for path, before, after in changes:
        path.write_bytes(after)
    print('Routed', len(changes), 'Capture One handlers; backups:', backup)
else:
    print('No original Capture One handlers for this prefix needed rerouting.')
PY
```

Finally, end the **stock Wine session for this dedicated prefix only**. All installers and configuration commands must have finished, with the editor and other prefix apps closed. `-k` terminates any remaining processes in that prefix, so do not use it with unsaved work. It does not target Affinity or other prefixes.

```bash
WINEPREFIX="$WINEPREFIX" /usr/bin/wineserver -k
WINEPREFIX="$WINEPREFIX" /usr/bin/wineserver -w
```

Use the new launcher for Capture One from now on. It selects the paired private Wine modules, XWayland, WineD3D/OpenGL and the browser-only GPU flag. The stock Wine commands above are setup commands, not an alternative application launcher. No Linux reboot is needed.

## 6. First launch, sign-in and one validation pass

Open **Capture One (Wine)** from the application menu or use:

```bash
"$HOME/.local/bin/capture-one-wine"
```

KDE may ask you to trust the new Desktop shortcut. Complete normal sign-in with your own licensed account. All compatibility files and settings are already in place; no intermediate unconfigured launch is required.

Use a new test session and copied photos. Check these in one pass:

| Check | Expected result / current limit |
| --- | --- |
| Sign-in | Editor opens after browser authentication |
| UI text and Layers + | Readable glyphs and menus; repeatedly open/close the menu |
| JPEG and supported Sony A1 ARW | Import and view both; move Exposure and inspect live updates |
| JPEG export | Export the edited RAW and inspect the resulting JPEG |
| Hardware Acceleration preferences | Select/confirm Auto and let kernel setup finish; OpenCL is separate from Windows AI features |
| AI acceleration and interactive features | DirectML startup/model benchmark passed and selected device 0; an AI Subject/Background mask worked in the user test. Test other AI tools and inspect their results; broader workflows remain unvalidated |
| Selection after previews finish | Image selection passed the hardware-WPF/full-frame user test. Recheck Library folder clicks, arrows and Select Next/Previous after previews finish and during longer use |
| Slider responsiveness | Sliders passed the latest hardware-WPF/full-frame user test; verify live photo updates on your own images |
| Tool-section expand/collapse | The user confirmed that tool drawers now close immediately with the NVIDIA EGL wait; retest repeated expansion and collapse |
| Window behavior | Test resize, maximize/restore and monitor moves; prior resize blinking remains unverified with this latest configuration |
| Longer editing | Check stability; a successful launch is not sufficient validation |

If changing an in-app preference requests a restart, follow that request. This reordered guide does not remove application-required restarts.

If a check fails, preserve the working configuration and record the failing operation before changing another component. Capture One logs can include credentials and private paths; share only reviewed diagnostic lines.

## Rollback

This procedure creates a separate prefix and private Wine runner; it does not replace system Wine or other applications. Save and close every app in this prefix before changing runners. Capture One can rename its process to `Main`, so a process-name check alone can miss a running editor. Never run different Wine versions simultaneously in the same prefix.

For an existing installation, preserve its original launcher, prefix settings and files before adapting this recipe. Restore the prior launcher/runner or restore **both** saved Unix modules together; never pair patched X11 with stock win32u. Restore only changed DLL overrides and newly added app-local DLLs/fonts from their backups. Rename `manifest.xml.disabled-for-wine` back only if the original name is free. Prefixes may hold licenses, accounts, catalogs and later edits: keep them private and do not overwrite current work with an old snapshot.

If updating an existing runner that already has both CodeWeavers/Valve fixes, save its `winex11.so` before adding the EGL wait. Restoring that saved module rolls back only the wait when its matching `win32u.so` has remained unchanged. Do not substitute a stock X11 module for that backup.

The handler originals are in the printed `$C1_BUILD/association-backups-*` directory. Restore only those corresponding desktop entries if rolling back launcher routing; keep them consistent with the runner you retain. Do not replace unrelated Wine handlers or change system MIME defaults.

To roll back only the D3D12 addition, close every app in this prefix, move the two newly added files `$C1_APP/d3d12.dll` and `$C1_APP/d3d12core.dll` out of the application directory, and remove only the `d3d12` and `d3d12core` values from `HKCU\Software\Wine\AppDefaults\CaptureOne.exe\DllOverrides` using the same private runner. For an adapted existing installation, restore its recorded prior values instead. Leave DXGI, D3D9, WPF, OpenCL and the color overrides unchanged. The prior DirectML initialization failure may return.

To undo only full-frame WPF, close Capture One and its helper. The originals are in `$C1_BUILD/runtimeconfig-before-full-frame`. Restore those two files only if they have not acquired other edits or been replaced by an app update; otherwise remove only the added `Switch.System.Windows.Media.MediaContext.DisableDirtyRectangles` property from each current JSON file. Restoring the earlier software-WPF fallback additionally means setting `HKCU\Software\Microsoft\Avalon.Graphics\DisableHWAcceleration` to DWORD `1` using the same private runner; it previously avoided the selection lag but made sliders slow. If adapting an existing setup, restore its recorded prior registry value instead. These changes do not require replacing graphics DLLs or changing OpenCL/DirectML.

## Attribution and licenses

The Wine patch includes two changes authored by **Paul Gofman, CodeWeavers**, published in Valve's Wine fork:

- [1dc8060af449d69cc4e8240732019224aab290b7](https://github.com/ValveSoftware/wine/commit/1dc8060af449d69cc4e8240732019224aab290b7)
- [d8a27b4712eaeb54f0a69e6dc98d39055a811ce2](https://github.com/ValveSoftware/wine/commit/d8a27b4712eaeb54f0a69e6dc98d39055a811ce2)

It also includes the locally written, guarded `eglWaitGL` call site described in Step 2. The underlying Present-completion implementation was authored by **Kyle Brenneman, NVIDIA**, in [commit 73680e0](https://github.com/NVIDIA/egl-x11/commit/73680e02218a031202faff79de3e7d683428d2dd); NVIDIA's implementation is provided by the installed driver/platform library and is not copied into this archive. The local Wine integration has not been accepted upstream.

The patch retains Wine source context and is licensed under [LGPL-2.1-or-later](LICENSE-LGPL-2.1.txt). The Wine 11 context adaptation initializes `needs_offscreen` to `FALSE` because this source lacks Proton's preceding fullscreen/offscreen block. Both matched Unix modules must be rebuilt together. This is not an official Wine or Capture One release.

`mscms-compat.c`/`mscms.def`, the two Python preparation helpers, the inline launcher and this documentation are independently written and licensed under [MIT](LICENSE-MIT.txt). The color proxy repairs Wine 11's standard-profile size query and forwards the remaining color API calls to matching Wine; it is separate from the published Wine fixes. See [Microsoft's API contract](https://learn.microsoft.com/en-us/windows/win32/api/icm/nf-icm-getstandardcolorspaceprofilew) and [Wine 11's implementation](https://github.com/wine-mirror/wine/blob/wine-11.0/dlls/mscms/profile.c).

Installer command references: [Microsoft .NET Windows installation](https://learn.microsoft.com/en-us/dotnet/core/install/windows#command-line-options), [WebView2 standalone deployment](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution#offline-deployment). The browser-only Windows 8 override relates to [Wine bug 58921](https://bugs.winehq.org/show_bug.cgi?id=58921); the main prefix stays on Windows 11. Application and font rights remain with their respective owners.
