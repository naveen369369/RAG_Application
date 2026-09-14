import { useMemo } from 'react'
import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

export function MarkdownRenderer({ content, className = '' }) {
  const html = useMemo(() => {
    if (!content) return ''
    try {
      return marked.parse(content)
    } catch {
      return content
    }
  }, [content])

  return (
    <div
      className={`chatgpt-markdown ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default MarkdownRenderer
