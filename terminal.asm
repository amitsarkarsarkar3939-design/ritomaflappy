; MASM x64 launcher. Build from the game folder with:
; ml64 /c terminal.asm && link /subsystem:console terminal.obj kernel32.lib

option casemap:none

EXTERN CreateProcessA:PROC
EXTERN WaitForSingleObject:PROC
EXTERN GetExitCodeProcess:PROC
EXTERN CloseHandle:PROC
EXTERN ExitProcess:PROC

.data
    commandLine     BYTE "python terminal.py --cli", 0
    startupInfo     BYTE 104 DUP(0)
    processInfo     BYTE 24 DUP(0)
    childExitCode   DWORD 127

.code
main PROC
    mov DWORD PTR [startupInfo], 104

    sub rsp, 58h
    xor ecx, ecx
    lea rdx, commandLine
    xor r8d, r8d
    xor r9d, r9d
    mov QWORD PTR [rsp + 20h], 1
    mov QWORD PTR [rsp + 28h], 0
    mov QWORD PTR [rsp + 30h], 0
    mov QWORD PTR [rsp + 38h], 0
    lea rax, startupInfo
    mov QWORD PTR [rsp + 40h], rax
    lea rax, processInfo
    mov QWORD PTR [rsp + 48h], rax
    call CreateProcessA
    add rsp, 58h
    test eax, eax
    jz launchFailed

    sub rsp, 28h
    mov rcx, QWORD PTR [processInfo]
    mov edx, 0FFFFFFFFh
    call WaitForSingleObject

    mov rcx, QWORD PTR [processInfo]
    lea rdx, childExitCode
    call GetExitCodeProcess

    mov rcx, QWORD PTR [processInfo + 8]
    call CloseHandle
    mov rcx, QWORD PTR [processInfo]
    call CloseHandle
    mov ecx, childExitCode
    call ExitProcess

launchFailed:
    sub rsp, 28h
    mov ecx, 127
    call ExitProcess
main ENDP

END
