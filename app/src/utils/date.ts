export function groupLabelForTimestamp(ts: number, now = Date.now()): string {
  const day = 24 * 60 * 60 * 1000;
  const startOfDay = (t: number) => {
    const d = new Date(t);
    d.setHours(0, 0, 0, 0);
    return d.getTime();
  };
  const today = startOfDay(now);
  const target = startOfDay(ts);
  const diffDays = Math.round((today - target) / day);

  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays <= 7) return 'Previous 7 days';
  if (diffDays <= 30) return 'Previous 30 days';

  const d = new Date(ts);
  const sameYear = d.getFullYear() === new Date(now).getFullYear();
  return d.toLocaleDateString(undefined, { month: 'long', year: sameYear ? undefined : 'numeric' });
}

const GROUP_ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days'];

export function groupOrderIndex(label: string): number {
  const idx = GROUP_ORDER.indexOf(label);
  return idx === -1 ? GROUP_ORDER.length : idx;
}

export function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let val = bytes / 1024;
  let i = 0;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}
