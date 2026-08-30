import { API_BASE } from './client'

export async function indexDocuments({ files, namespace, strategy, chunkSize, chunkOverlap }) {
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  const params = new URLSearchParams({
    namespace,
    chunking_strategy: strategy,
    chunk_size: String(chunkSize),
    chunk_overlap: String(chunkOverlap),
  })
  const res = await fetch(`${API_BASE}/index?${params}`, {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}
