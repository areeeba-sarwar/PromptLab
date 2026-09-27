import Image from 'next/image'

export function PromptLabIcon({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <Image
      src="/logo.png"
      alt="PromptLab"
      width={size}
      height={size}
      className={className}
    />
  )
}
