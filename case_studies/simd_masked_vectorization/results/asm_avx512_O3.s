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
	jle	.L54
	leal	-1(%rdx), %eax
	cmpl	$14, %eax
	jbe	.L24
	movl	%edx, %esi
	xorl	%eax, %eax
	vxorps	%xmm1, %xmm1, %xmm1
	shrl	$4, %esi
	salq	$6, %rsi
	.p2align 4,,10
	.p2align 3
.L4:
	vcmpps	$1, (%rdi,%rax), %zmm1, %k1
	vsqrtps	(%rdi,%rax), %zmm0{%k1}{z}
	vmovups	%zmm0, (%rcx,%rax)
	addq	$64, %rax
	cmpq	%rax, %rsi
	jne	.L4
	movl	%edx, %eax
	andl	$-16, %eax
	movl	%eax, %esi
	cmpl	%eax, %edx
	je	.L53
.L3:
	movl	%edx, %r8d
	subl	%esi, %r8d
	leal	-1(%r8), %r9d
	cmpl	$6, %r9d
	jbe	.L8
	vsqrtps	(%rdi,%rsi,4), %ymm1
	vxorps	%xmm0, %xmm0, %xmm0
	vcmpltps	(%rdi,%rsi,4), %ymm0, %ymm0
	vandps	%ymm1, %ymm0, %ymm0
	vmovups	%ymm0, (%rcx,%rsi,4)
	movl	%r8d, %esi
	andl	$-8, %esi
	addl	%esi, %eax
	andl	$7, %r8d
	je	.L53
.L8:
	movslq	%eax, %r8
	vxorps	%xmm1, %xmm1, %xmm1
	vmovss	(%rdi,%r8,4), %xmm0
	leaq	0(,%r8,4), %rsi
	leaq	(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L41
	vsqrtss	%xmm0, %xmm0, %xmm0
.L10:
	vmovss	%xmm0, (%r8)
	leal	1(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L53
	vmovss	4(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	4(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L42
	vsqrtss	%xmm0, %xmm0, %xmm0
.L12:
	vmovss	%xmm0, (%r8)
	leal	2(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L53
	vmovss	8(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	8(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L43
	vsqrtss	%xmm0, %xmm0, %xmm0
.L14:
	vmovss	%xmm0, (%r8)
	leal	3(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L53
	vmovss	12(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	12(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L44
	vsqrtss	%xmm0, %xmm0, %xmm0
.L16:
	vmovss	%xmm0, (%r8)
	leal	4(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L53
	vmovss	16(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	16(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L45
	vsqrtss	%xmm0, %xmm0, %xmm0
.L18:
	vmovss	%xmm0, (%r8)
	leal	5(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L53
	vmovss	20(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	20(%rcx,%rsi), %r8
	vcomiss	%xmm1, %xmm0
	jbe	.L46
	vsqrtss	%xmm0, %xmm0, %xmm0
.L20:
	addl	$6, %eax
	vmovss	%xmm0, (%r8)
	cmpl	%eax, %edx
	jle	.L53
	vmovss	24(%rdi,%rsi), %xmm0
	vxorps	%xmm1, %xmm1, %xmm1
	leaq	24(%rcx,%rsi), %rax
	vcomiss	%xmm1, %xmm0
	jbe	.L56
	vsqrtss	%xmm0, %xmm0, %xmm0
	vmovss	%xmm0, (%rax)
	vzeroupper
	ret
	.p2align 4,,10
	.p2align 3
.L53:
	vzeroupper
.L54:
	ret
	.p2align 4,,10
	.p2align 3
.L41:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L10
	.p2align 4,,10
	.p2align 3
.L42:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L12
	.p2align 4,,10
	.p2align 3
.L43:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L14
	.p2align 4,,10
	.p2align 3
.L44:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L16
	.p2align 4,,10
	.p2align 3
.L45:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L18
	.p2align 4,,10
	.p2align 3
.L46:
	vxorps	%xmm0, %xmm0, %xmm0
	jmp	.L20
	.p2align 4,,10
	.p2align 3
.L56:
	vmovaps	%xmm1, %xmm0
	vmovss	%xmm0, (%rax)
	vzeroupper
	ret
.L24:
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
