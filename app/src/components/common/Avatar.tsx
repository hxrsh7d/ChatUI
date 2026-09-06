interface Props {
  name: string;
  size?: number;
  src?: string;
}

export function Avatar({ name, size = 28, src }: Props) {
  const initials = name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        style={{ width: size, height: size }}
        className="rounded-full object-cover shrink-0"
      />
    );
  }

  return (
    <div
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      className="flex shrink-0 items-center justify-center rounded-full bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900 font-medium"
    >
      {initials || '?'}
    </div>
  );
}
