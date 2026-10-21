	.file	"kernel.c"
	.text
	.p2align 4
	.globl	kernel
	.type	kernel, @function
kernel:
.LFB0:
	.cfi_startproc
	endbr64
	movq	%rsi, %rcx
	testl	%edx, %edx
	jle	.L28
	leal	-1(%rdx), %eax
	cmpl	$6, %eax
	jbe	.L16
	movl	%edx, %esi
	xorl	%eax, %eax
	vxorps	%xmm2, %xmm2, %xmm2
	shrl	$3, %esi
	salq	$5, %rsi
	.p2align 4,,10
	.p2align 3
.L4:
	vsqrtps	(%rdi,%rax), %ymm1
	vcmpltps	(%rdi,%rax), %ymm2, %ymm0
	vandps	%ymm1, %ymm0, %ymm0
	vmovups	%ymm0, (%rcx,%rax)
	addq	$32, %rax
	cmpq	%rax, %rsi
	jne	.L4
	movl	%edx, %eax
	andl	$-8, %eax
	movl	%eax, %esi
	cmpl	%eax, %edx
	je	.L30
	vzeroupper
.L3:
	movl	%edx, %r8d
	subl	%esi, %r8d
	leal	-1(%r8), %r9d
	cmpl	$2, %r9d
	jbe	.L8
	vsqrtps	(%rdi,%rsi,4), %xmm1
	vxorps	%xmm0, %xmm0, %xmm0
	vcmpltps	(%rdi,%rsi,4), %xmm0, %xmm0
	vandps	%xmm1, %xmm0, %xmm0
	vmovups	%xmm0, (%rcx,%rsi,4)
	movl	%r8d, %esi
	andl	$-4, %esi
	addl	%esi, %eax
	andl	$3, %r8d
	je	.L28
.L8:
	movslq	%eax, %r8
	vxorps	%xmm1, %xmm1, %xmm1
	vmovss	(%rdi,%r8,4), %xmm0
	leaq	0(,%r8,4), %rsi
	leaq	(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L25
	vsqrtss	%xmm0, %xmm0, %xmm0
.L10:
	vmovss	%xmm0, (%r8)
	leal	1(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L28
	vmovss	4(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	4(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L26
	vsqrtss	%xmm0, %xmm0, %xmm0
.L12:
	addl	$2, %eax
	vmovss	%xmm0, (%r8)
	cmpl	%eax, %edx
	jle	.L28
	vmovss	8(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	8(%rcx,%rsi), %rax
	vcomiss	%xmm1, %xmm0
	jbe	.L31
	vsqrtss	%xmm0, %xmm0, %xmm0
	vmovss	%xmm0, (%rax)
	ret
	.p2align 4,,10
	.p2align 3
.L28:
	ret
	.p2align 4,,10
	.p2align 3
.L25:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L10
	.p2align 4,,10
	.p2align 3
.L26:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L12
	.p2align 4,,10
	.p2align 3
.L31:
	vmovaps	%xmm1, %xmm0
	vmovss	%xmm0, (%rax)
	ret
	.p2align 4,,10
	.p2align 3
.L30:
	vzeroupper
	ret
.L16:
	xorl	%esi, %esi
	xorl	%eax, %eax
	jmp	.L3
	.cfi_endproc
.LFE0:
	.size	kernel, .-kernel
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x3
3:
	.align 8
4:
