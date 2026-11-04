import { getSelectedAccount, PRIMARY_ACCOUNT } from './account'

/**
 * Returns the add-on's API root, without an account.
 * Under HA ingress (subpath), derives from current location so relative requests resolve correctly.
 */
export function getRootApiBase(): string {
  if (typeof window === 'undefined') {
    return '/api'
  }
  const pathname = window.location.pathname.replace(/\/$/, '')
  if (!pathname || pathname === '/' || pathname === '/index' || pathname === '/index.html') {
    return '/api'
  }
  return pathname + '/api'
}

/**
 * Returns the API base URL for fetch calls, for the ConEd account the panel shows.
 * The primary account uses the plain /api root.
 */
export function getApiBase(): string {
  const account = getSelectedAccount()
  const root = getRootApiBase()
  if (account === PRIMARY_ACCOUNT) {
    return root
  }
  return `${root}/a/${encodeURIComponent(account)}`
}
