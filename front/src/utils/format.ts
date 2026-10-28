export function dateOf(iso: string): string {
  return (iso || '').slice(0, 10)
}

export function datetimeOf(iso: string): string {
  return (iso || '').replace('T', ' ').slice(0, 19)
}
