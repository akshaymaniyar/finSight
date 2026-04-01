import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { getCategories } from '../api/categories';
import type { Category } from '../api/categories';

interface CategorySelectProps {
  value: string;
  subValue?: string | null;
  onChange: (category: string, subCategory: string | null) => void;
  onClose?: () => void;
  compact?: boolean;
}

export default function CategorySelect({
  value,
  subValue,
  onChange,
  onClose,
  compact = false,
}: CategorySelectProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [expandedParent, setExpandedParent] = useState<number | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 60000,
  });

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
        onClose?.();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  if (!isOpen || !categories) return null;

  const expenseCategories = categories.filter((c) => !c.is_income);
  const incomeCategories = categories.filter((c) => c.is_income);

  const handleSelect = (parent: Category, subName: string | null) => {
    onChange(parent.name, subName);
    setIsOpen(false);
    onClose?.();
  };

  const renderCategory = (cat: Category) => {
    const isExpanded = expandedParent === cat.id;
    const isSelected = value === cat.name;

    return (
      <div key={cat.id}>
        <div
          className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-indigo-50 transition-colors ${
            isSelected && !subValue ? 'bg-indigo-50 text-indigo-700' : ''
          }`}
          onClick={() => {
            if (cat.subcategories.length > 0) {
              setExpandedParent(isExpanded ? null : cat.id);
            } else {
              handleSelect(cat, null);
            }
          }}
        >
          <div
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: cat.color || '#9E9E9E' }}
          />
          {cat.subcategories.length > 0 ? (
            isExpanded ? (
              <ChevronDown size={10} className="text-gray-400 shrink-0" />
            ) : (
              <ChevronRight size={10} className="text-gray-400 shrink-0" />
            )
          ) : (
            <div className="w-[10px]" />
          )}
          <span className={`text-xs font-medium ${isSelected && !subValue ? 'text-indigo-700' : 'text-gray-700'}`}>
            {cat.name}
          </span>
        </div>

        {/* Subcategories */}
        {isExpanded && cat.subcategories.map((sub) => {
          const isSubSelected = value === cat.name && subValue === sub.name;
          return (
            <div
              key={sub.id}
              className={`flex items-center gap-2 pl-9 pr-3 py-1 cursor-pointer hover:bg-indigo-50 transition-colors ${
                isSubSelected ? 'bg-indigo-100 text-indigo-700' : ''
              }`}
              onClick={() => handleSelect(cat, sub.name)}
            >
              <span className={`text-xs ${isSubSelected ? 'text-indigo-700 font-medium' : 'text-gray-600'}`}>
                {sub.name}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      ref={ref}
      className={`absolute z-50 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden ${
        compact ? 'w-56' : 'w-64'
      }`}
      style={{ maxHeight: '320px', overflowY: 'auto' }}
    >
      {/* Expense categories */}
      <div className="px-3 pt-2 pb-1">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Expenses</span>
      </div>
      {expenseCategories.map(renderCategory)}

      {/* Income categories */}
      <div className="px-3 pt-2 pb-1 border-t border-gray-100">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Income</span>
      </div>
      {incomeCategories.map(renderCategory)}
    </div>
  );
}
