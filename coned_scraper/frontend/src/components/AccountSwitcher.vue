<template>
  <div v-if="accounts.length > 1" class="account-switcher">
    <label class="account-switcher-label" for="coned-account-select">Account</label>
    <select
      id="coned-account-select"
      class="account-switcher-select"
      :value="selected"
      @change="onChange(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="a in accounts" :key="a.key" :value="a.key">
        {{ a.label }}{{ a.number ? ` (${a.number})` : '' }}
      </option>
    </select>
    <button
      type="button"
      class="account-switcher-rename"
      title="Rename this account"
      aria-label="Rename this account"
      @click="rename"
    >
      ✏️
    </button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getRootApiBase } from '../lib/api-base'
import { getSelectedAccount, setSelectedAccount, PRIMARY_ACCOUNT } from '../lib/account'

interface ConEdAccount {
  key: string
  label: string
  number: string | null
  address: string | null
  is_primary: boolean
}

const accounts = ref<ConEdAccount[]>([])
const selected = ref(getSelectedAccount())

async function load() {
  try {
    const res = await fetch(`${getRootApiBase()}/accounts`)
    if (!res.ok) return
    const data = await res.json()
    accounts.value = Array.isArray(data.accounts) ? data.accounts : []
    // The saved choice no longer exists (e.g. account removed): fall back to primary
    if (!accounts.value.some((a) => a.key === selected.value)) {
      if (selected.value !== PRIMARY_ACCOUNT) {
        setSelectedAccount(PRIMARY_ACCOUNT)
        window.location.reload()
      }
    }
  } catch {
    accounts.value = []
  }
}

function onChange(key: string) {
  if (key === selected.value) return
  setSelectedAccount(key)
  // Reload so every view fetches the new account's data from scratch
  window.location.reload()
}

async function rename() {
  const current = accounts.value.find((a) => a.key === selected.value)
  if (!current) return
  const label = window.prompt('Name for this account', current.label)
  if (label === null || !label.trim() || label.trim() === current.label) return
  const res = await fetch(`${getRootApiBase()}/accounts/${encodeURIComponent(current.key)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label.trim() }),
  })
  if (res.ok) {
    current.label = (await res.json()).label
  }
}

onMounted(load)
</script>

<style scoped>
.account-switcher {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: white;
}

.account-switcher-label {
  font-size: 0.8rem;
  opacity: 0.85;
}

.account-switcher-select {
  background: rgba(255, 255, 255, 0.12);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 6px;
  padding: 0.3rem 0.5rem;
  font-size: 0.85rem;
  max-width: 260px;
}

.account-switcher-select option {
  color: #1f2937;
}

.account-switcher-rename {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0.2rem;
}
</style>
