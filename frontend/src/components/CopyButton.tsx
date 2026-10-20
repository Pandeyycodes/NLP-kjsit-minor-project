import { useEffect, useState } from 'react'

interface Props {
  label: string
  getText: () => string
}

export default function CopyButton({ label, getText }: Props) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')

  useEffect(() => {
    if (state === 'idle') return
    const timer = setTimeout(() => setState('idle'), 2000)
    return () => clearTimeout(timer)
  }, [state])

  async function copy() {
    try {
      await navigator.clipboard.writeText(getText())
      setState('copied')
    } catch {
      setState('failed')
    }
  }

  return (
    <button type="button" className="button button-quiet" onClick={copy}>
      {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : label}
    </button>
  )
}
