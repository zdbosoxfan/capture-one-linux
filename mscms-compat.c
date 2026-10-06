/* App-scoped Wine API compatibility proxy. Does not change Capture One.
 * Repairs size-query semantics of GetStandardColorSpaceProfile[A/W].
 * All other exports forward to the original Wine implementation.
 * Independently written implementation; MIT license.
 */
#include <windows.h>

typedef BOOL (WINAPI *get_w_fn)(PCWSTR,DWORD,PWSTR,PDWORD);
typedef BOOL (WINAPI *get_a_fn)(PCSTR,DWORD,PSTR,PDWORD);
static INIT_ONCE once = INIT_ONCE_STATIC_INIT;
static HMODULE original;
static BOOL CALLBACK initialize(PINIT_ONCE unused, PVOID parameter, PVOID *context)
{
    HMODULE own = NULL;
    WCHAR path[32768];
    DWORD length;
    (void)unused; (void)parameter; (void)context;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCWSTR)&initialize, &own)) return FALSE;
    length = GetModuleFileNameW(own,path,32768);
    if (!length || length >= 32740) return FALSE;
    while (length && path[length-1] != L'\\') --length;
    if (!length) return FALSE;
    lstrcpyW(path+length,L"mscms_wine.dll");
    original = LoadLibraryW(path);
    return original != NULL;
}

__declspec(dllexport) BOOL WINAPI GetStandardColorSpaceProfileW(
    PCWSTR machine,DWORD id,PWSTR profile,PDWORD size)
{
    WCHAR temporary[32768];
    DWORD capacity = sizeof(temporary), required, supplied;
    get_w_fn get_original;
    if (!size) { SetLastError(ERROR_INVALID_PARAMETER); return FALSE; }
    if (!InitOnceExecuteOnce(&once,initialize,NULL,NULL)) return FALSE;
    get_original = (get_w_fn)GetProcAddress(original,"GetStandardColorSpaceProfileW");
    if (!get_original) return FALSE;
    if (!get_original(machine,id,temporary,&capacity)) return FALSE;
    required = (lstrlenW(temporary)+1)*sizeof(WCHAR);
    supplied = *size;
    *size = required;
    if (!profile || supplied < required) {
        SetLastError(ERROR_INSUFFICIENT_BUFFER);
        return FALSE;
    }
    CopyMemory(profile,temporary,required);
    return TRUE;
}

__declspec(dllexport) BOOL WINAPI GetStandardColorSpaceProfileA(
    PCSTR machine,DWORD id,PSTR profile,PDWORD size)
{
    CHAR temporary[32768];
    DWORD capacity = sizeof(temporary), required, supplied;
    get_a_fn get_original;
    if (!size) { SetLastError(ERROR_INVALID_PARAMETER); return FALSE; }
    if (!InitOnceExecuteOnce(&once,initialize,NULL,NULL)) return FALSE;
    get_original = (get_a_fn)GetProcAddress(original,"GetStandardColorSpaceProfileA");
    if (!get_original) return FALSE;
    if (!get_original(machine,id,temporary,&capacity)) return FALSE;
    required = lstrlenA(temporary)+1;
    supplied = *size;
    *size = required;
    if (!profile || supplied < required) {
        SetLastError(ERROR_INSUFFICIENT_BUFFER);
        return FALSE;
    }
    CopyMemory(profile,temporary,required);
    return TRUE;
}
