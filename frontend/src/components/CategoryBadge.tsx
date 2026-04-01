import { getCategoryColor } from '../utils/formatters';

interface CategoryBadgeProps {
  category: string;
  onClick?: () => void;
  clickable?: boolean;
}

export default function CategoryBadge({ category, onClick, clickable = false }: CategoryBadgeProps) {
  const color = getCategoryColor(category);

  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        clickable ? 'cursor-pointer hover:opacity-80' : ''
      }`}
      style={{
        backgroundColor: color + '18',
        color: color,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {category}
    </span>
  );
}
