# Windows engine inputs and staging evidence — 1.0.1rc2 source candidate

These are SHA-256 digests of the **checked-in, unchanged Windows native inputs** as inspected on Kali during STEP 04. Repository notices identify the engine as GoodbyeDPI v0.2.3rc3 and WinDivert v2.2.0; matching these files to the exact upstream source and driver signature still requires release review. No binary was downloaded, rebuilt or replaced here.

| Input | SHA-256 |
| --- | --- |
| `bin/x86/goodbyedpi.exe` | `66e202c9fce9e769e2bc791b7fd6f56f21eab59f607f4ed0724e0c68c430dd1f` |
| `bin/x86/WinDivert.dll` | `625ffdd95bfabff32d0e8a95beabcd303c01c8bba73b90402d4e84d6e15dd8e5` |
| `bin/x86/WinDivert32.sys` | `29ca5ceb59c9c6993a349e82b1fd46078e6f8a302764153ab84fa22e382fcdca` |
| `bin/x86/WinDivert64.sys` | `e69b5ba3f0cd6cfb2983e442636e7f0b342b61b15264b0328317d4559c82cf50` |
| `bin/x86_64/goodbyedpi.exe` | `8d412b094bb9c137ff25ba9a794d1122ecc84bb776debff6c249723a13cc31cd` |
| `bin/x86_64/WinDivert.dll` | `6110bfa44667405179c3e15e12af1b62037e447ed59b054b19042032995e6c7e` |
| `bin/x86_64/WinDivert64.sys` | `e69b5ba3f0cd6cfb2983e442636e7f0b342b61b15264b0328317d4559c82cf50` |

The existing runner hashes each architecture's filename plus content in order before staging. Expected folder names under `%ProgramFiles%\GoodbyeDPI-Turkey\engine\` for this exact source tree are:

- x86: `12f2b05f074e3ee2d5e4c4df079a84193940d88131977106ba252306a2945019`
- x86_64: `ccf4b3e19cc39ba85a5b78e69ace4c19b1afdc79582177f57167a50edb707cfe`

`src/utils/runner.py` starts the staged executable by absolute path. Its EXE, DLL and driver remain together in the stable staging folder; the runner verifies staged bytes before launch. The Windows loader's application-directory DLL resolution should find the adjacent WinDivert DLL, but the final native test must inspect the actual image path, loaded DLL, driver service path and cleanup behavior. No code here changes the engine arguments, working directory, loader search path, service ownership or Quit logic. Staged folders are not deleted automatically because an existing service may still refer to them.

`tools/windows/inspect_rc.py` will compare the final frozen archive's engine files, logo and notices byte for byte with these source inputs. The Windows build script records source-manifest, wheels, engine, EXE and portable hashes. These static checks do not validate UAC, network function, driver signature or `_MEI` cleanup.
