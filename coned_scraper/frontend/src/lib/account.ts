/**
 * The ConEd account the panel is showing. One ConEd login can hold several
 * accounts; the add-on serves each one under /api/a/<key>/...
 * "primary" is the account that existed before multi-account support.
 */
export const PRIMARY_ACCOUNT = 'primary'
const STORAGE_KEY = 'ha-coned:account'

export function getSelectedAccount(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || PRIMARY_ACCOUNT
  } catch {
    return PRIMARY_ACCOUNT
  }
}

export function setSelectedAccount(key: string): void {
  try {
    if (!key || key === PRIMARY_ACCOUNT) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, key)
    }
  } catch {
    // Blocked storage: the panel stays on the primary account.
  }
}
