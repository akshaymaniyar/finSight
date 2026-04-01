import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Edit2,
  Trash2,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Tag,
} from 'lucide-react';
import { getCategories, createCategory, updateCategory, deleteCategory } from '../api/categories';
import type { Category, Subcategory } from '../api/categories';
import LoadingSpinner from '../components/LoadingSpinner';

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editKeywords, setEditKeywords] = useState('');
  const [newCatName, setNewCatName] = useState('');
  const [newSubName, setNewSubName] = useState('');
  const [addingSubTo, setAddingSubTo] = useState<number | null>(null);
  const [showAddParent, setShowAddParent] = useState(false);

  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  });

  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setNewCatName('');
      setNewSubName('');
      setAddingSubTo(null);
      setShowAddParent(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; name?: string; keywords?: string }) =>
      updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  });

  const startEdit = (cat: Category | Subcategory, keywords?: string) => {
    setEditingId(cat.id);
    setEditName(cat.name);
    setEditKeywords(keywords || (cat as Subcategory).keywords || '');
  };

  const saveEdit = (isSubcategory: boolean) => {
    if (!editingId || !editName.trim()) return;
    const payload: { id: number; name?: string; keywords?: string } = {
      id: editingId,
      name: editName.trim(),
    };
    if (isSubcategory) {
      payload.keywords = editKeywords;
    }
    updateMutation.mutate(payload);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading categories..." />
      </div>
    );
  }

  const expenseCategories = (categories || []).filter((c) => !c.is_income);
  const incomeCategories = (categories || []).filter((c) => c.is_income);

  return (
    <div className="p-4 lg:p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your expense and income categories. Each category has subcategories with auto-match keywords.
          </p>
        </div>
        <button
          onClick={() => setShowAddParent(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Add Category
        </button>
      </div>

      {/* Add new parent category */}
      {showAddParent && (
        <div className="bg-white rounded-xl border border-indigo-200 p-4 flex items-center gap-3">
          <input
            type="text"
            value={newCatName}
            onChange={(e) => setNewCatName(e.target.value)}
            placeholder="New category name..."
            autoFocus
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
          />
          <button
            onClick={() => createMutation.mutate({ name: newCatName })}
            disabled={!newCatName.trim() || createMutation.isPending}
            className="p-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
          >
            <Check size={16} />
          </button>
          <button
            onClick={() => { setShowAddParent(false); setNewCatName(''); }}
            className="p-2 bg-gray-200 text-gray-600 rounded-lg hover:bg-gray-300"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Expense categories */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Expense Categories
        </h2>
        <div className="space-y-2">
          {expenseCategories.map((cat) => (
            <CategoryCard
              key={cat.id}
              category={cat}
              isExpanded={expandedId === cat.id}
              onToggle={() => setExpandedId(expandedId === cat.id ? null : cat.id)}
              editingId={editingId}
              editName={editName}
              editKeywords={editKeywords}
              onEditNameChange={setEditName}
              onEditKeywordsChange={setEditKeywords}
              onStartEdit={startEdit}
              onSaveEdit={saveEdit}
              onCancelEdit={() => setEditingId(null)}
              onDelete={(id) => deleteMutation.mutate(id)}
              addingSubTo={addingSubTo}
              newSubName={newSubName}
              onNewSubNameChange={setNewSubName}
              onStartAddSub={() => setAddingSubTo(cat.id)}
              onAddSub={() => createMutation.mutate({ name: newSubName, parent_id: cat.id })}
              onCancelAddSub={() => { setAddingSubTo(null); setNewSubName(''); }}
              isCreating={createMutation.isPending}
            />
          ))}
        </div>
      </div>

      {/* Income categories */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Income Categories
        </h2>
        <div className="space-y-2">
          {incomeCategories.map((cat) => (
            <CategoryCard
              key={cat.id}
              category={cat}
              isExpanded={expandedId === cat.id}
              onToggle={() => setExpandedId(expandedId === cat.id ? null : cat.id)}
              editingId={editingId}
              editName={editName}
              editKeywords={editKeywords}
              onEditNameChange={setEditName}
              onEditKeywordsChange={setEditKeywords}
              onStartEdit={startEdit}
              onSaveEdit={saveEdit}
              onCancelEdit={() => setEditingId(null)}
              onDelete={(id) => deleteMutation.mutate(id)}
              addingSubTo={addingSubTo}
              newSubName={newSubName}
              onNewSubNameChange={setNewSubName}
              onStartAddSub={() => setAddingSubTo(cat.id)}
              onAddSub={() => createMutation.mutate({ name: newSubName, parent_id: cat.id })}
              onCancelAddSub={() => { setAddingSubTo(null); setNewSubName(''); }}
              isCreating={createMutation.isPending}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function CategoryCard({
  category,
  isExpanded,
  onToggle,
  editingId,
  editName,
  editKeywords,
  onEditNameChange,
  onEditKeywordsChange,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDelete,
  addingSubTo,
  newSubName,
  onNewSubNameChange,
  onStartAddSub,
  onAddSub,
  onCancelAddSub,
  isCreating,
}: {
  category: Category;
  isExpanded: boolean;
  onToggle: () => void;
  editingId: number | null;
  editName: string;
  editKeywords: string;
  onEditNameChange: (v: string) => void;
  onEditKeywordsChange: (v: string) => void;
  onStartEdit: (cat: Category | Subcategory, keywords?: string) => void;
  onSaveEdit: (isSub: boolean) => void;
  onCancelEdit: () => void;
  onDelete: (id: number) => void;
  addingSubTo: number | null;
  newSubName: string;
  onNewSubNameChange: (v: string) => void;
  onStartAddSub: () => void;
  onAddSub: () => void;
  onCancelAddSub: () => void;
  isCreating: boolean;
}) {
  const isEditing = editingId === category.id;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Parent row */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggle}
      >
        {isExpanded ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}

        <div
          className="w-3 h-3 rounded-full shrink-0"
          style={{ backgroundColor: category.color || '#9E9E9E' }}
        />

        {isEditing ? (
          <input
            type="text"
            value={editName}
            onChange={(e) => onEditNameChange(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            autoFocus
            className="flex-1 px-2 py-1 border border-indigo-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        ) : (
          <span className="flex-1 text-sm font-semibold text-gray-900">{category.name}</span>
        )}

        <span className="text-xs text-gray-400">{category.subcategories.length} subcategories</span>

        {isEditing ? (
          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => onSaveEdit(false)} className="p-1.5 text-green-600 hover:bg-green-50 rounded"><Check size={14} /></button>
            <button onClick={onCancelEdit} className="p-1.5 text-gray-400 hover:bg-gray-100 rounded"><X size={14} /></button>
          </div>
        ) : (
          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => onStartEdit(category)} className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded"><Edit2 size={14} /></button>
            {!category.is_system && (
              <button onClick={() => onDelete(category.id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"><Trash2 size={14} /></button>
            )}
          </div>
        )}
      </div>

      {/* Subcategories */}
      {isExpanded && (
        <div className="border-t border-gray-100 bg-gray-50/50">
          {category.subcategories.map((sub) => {
            const isSubEditing = editingId === sub.id;
            return (
              <div
                key={sub.id}
                className="flex items-center gap-3 px-4 py-2.5 pl-12 border-b border-gray-100 last:border-b-0"
              >
                <Tag size={12} className="text-gray-300 shrink-0" />

                {isSubEditing ? (
                  <div className="flex-1 space-y-1.5">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => onEditNameChange(e.target.value)}
                      autoFocus
                      className="w-full px-2 py-1 border border-indigo-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <input
                      type="text"
                      value={editKeywords}
                      onChange={(e) => onEditKeywordsChange(e.target.value)}
                      placeholder="Keywords (comma-separated)..."
                      className="w-full px-2 py-1 border border-gray-200 rounded text-xs text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                ) : (
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-gray-700">{sub.name}</span>
                    {sub.keywords && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">
                        {sub.keywords}
                      </p>
                    )}
                  </div>
                )}

                {isSubEditing ? (
                  <div className="flex gap-1">
                    <button onClick={() => onSaveEdit(true)} className="p-1.5 text-green-600 hover:bg-green-50 rounded"><Check size={14} /></button>
                    <button onClick={onCancelEdit} className="p-1.5 text-gray-400 hover:bg-gray-100 rounded"><X size={14} /></button>
                  </div>
                ) : (
                  <div className="flex gap-1">
                    <button onClick={() => onStartEdit(sub, sub.keywords || '')} className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded"><Edit2 size={12} /></button>
                    {!category.is_system && (
                      <button onClick={() => onDelete(sub.id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"><Trash2 size={12} /></button>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Add subcategory */}
          {addingSubTo === category.id ? (
            <div className="flex items-center gap-2 px-4 py-2.5 pl-12">
              <input
                type="text"
                value={newSubName}
                onChange={(e) => onNewSubNameChange(e.target.value)}
                placeholder="Subcategory name..."
                autoFocus
                className="flex-1 px-2 py-1 border border-indigo-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button onClick={onAddSub} disabled={!newSubName.trim() || isCreating} className="p-1.5 text-green-600 hover:bg-green-50 rounded disabled:opacity-50"><Check size={14} /></button>
              <button onClick={onCancelAddSub} className="p-1.5 text-gray-400 hover:bg-gray-100 rounded"><X size={14} /></button>
            </div>
          ) : (
            <button
              onClick={onStartAddSub}
              className="flex items-center gap-2 px-4 py-2 pl-12 w-full text-xs text-indigo-600 hover:bg-indigo-50 transition-colors"
            >
              <Plus size={12} />
              Add subcategory
            </button>
          )}
        </div>
      )}
    </div>
  );
}
