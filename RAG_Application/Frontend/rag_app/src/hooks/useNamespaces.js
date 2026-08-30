import { useState, useEffect } from 'react'
import { fetchNamespaces } from '../api/namespaces'

export function useNamespaces() {
  const [namespaces, setNamespaces] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchNamespaces()
      .then(setNamespaces)
      .catch(() => setNamespaces([]))
      .finally(() => setLoading(false))
  }, [])

  return { namespaces, loading }
}
