import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  User,
  Calendar,
  CreditCard,
  Phone,
  Shield,
  ArrowRight,
  Check,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { getProfile, updateProfile } from '../api/profile';
import type { ProfileUpdateData } from '../api/profile';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/LoadingSpinner';

const BANK_PASSWORD_INFO: Record<string, string> = {
  'HDFC': 'CC: First 4 letters of name + Last 4 digits of card. Account: Customer ID or DOB (DDMMYYYY)',
  'ICICI': 'First 4 letters of name (UPPER) + DOB (DDMM)',
  'IDFC First': 'DOB in DDMMYYYY format',
  'Axis Bank': 'First 4 letters of name (UPPER) + DOB (DDMM)',
  'SBI': 'CC: First 4 letters + DOB (DDMM). Account: Last 5 mobile digits + DOB (DDMMYY)',
  'Kotak': 'CC: First 4 letters (lowercase) + DOB (DDMM). Account: CRN number',
  'Amex': 'First 4 letters of name (UPPER) + DOB (DDMM)',
  'Yes Bank': 'Customer ID (CIF) + DOB (DDMMYYYY)',
  'IndusInd': 'CC: First 4 letters (lowercase) + DOB (DDMM)',
};

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user: authUser, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const [showBankInfo, setShowBankInfo] = useState(false);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [dob, setDob] = useState('');
  const [panFirst5, setPanFirst5] = useState('');
  const [mobileLast5, setMobileLast5] = useState('');
  const [customerIds, setCustomerIds] = useState<Record<string, string>>({});

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  });

  // Populate form with existing data
  useEffect(() => {
    if (profile) {
      setFirstName(profile.first_name || '');
      setLastName(profile.last_name || '');
      setDob(profile.dob || '');
      setPanFirst5(profile.pan_first5 || '');
      setMobileLast5(profile.mobile_last5 || '');
      setCustomerIds(profile.customer_ids || {});
    }
  }, [profile]);

  // Pre-fill from Google name
  useEffect(() => {
    if (authUser?.name && !firstName && !profile?.first_name) {
      const parts = authUser.name.split(' ');
      setFirstName(parts[0] || '');
      setLastName(parts.slice(1).join(' ') || '');
    }
  }, [authUser, firstName, profile]);

  const saveMutation = useMutation({
    mutationFn: (data: ProfileUpdateData) => updateProfile(data),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      await refreshUser();
      navigate('/sync');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: ProfileUpdateData = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
    };
    if (dob) data.dob = dob;
    if (panFirst5) data.pan_first5 = panFirst5.trim();
    if (mobileLast5) data.mobile_last5 = mobileLast5.trim();

    // Only include non-empty customer IDs
    const filtered = Object.fromEntries(
      Object.entries(customerIds).filter(([, v]) => v.trim())
    );
    if (Object.keys(filtered).length > 0) data.customer_ids = filtered;

    saveMutation.mutate(data);
  };

  const handleSkip = () => {
    navigate('/sync');
  };

  const handleCustomerIdChange = (bank: string, value: string) => {
    setCustomerIds((prev) => ({ ...prev, [bank]: value }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading profile..." />
      </div>
    );
  }

  const isFirstTime = !profile?.profile_completed;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        {isFirstTime && (
          <div className="bg-indigo-600 text-white rounded-2xl p-6 mb-6">
            <h1 className="text-xl font-bold mb-2">Complete Your Profile</h1>
            <p className="text-indigo-200 text-sm">
              We need a few details to automatically open your password-protected bank statement
              PDFs. This information is stored securely on your server and never shared.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              <User size={18} className="text-indigo-600" />
              <h2 className="text-base font-semibold text-gray-900">Basic Information</h2>
              <span className="text-xs text-red-500 font-medium ml-auto">Required</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="As on bank account"
                  required
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
                <p className="text-xs text-gray-400 mt-1">
                  First 4 letters used for most bank passwords
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="As on bank account"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                <Calendar size={14} />
                Date of Birth
              </label>
              <input
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                required
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-400 mt-1">
                Used in DOB-based password patterns (DDMM, DDMMYYYY)
              </p>
            </div>
          </div>

          {/* Optional Info */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Shield size={18} className="text-indigo-600" />
              <h2 className="text-base font-semibold text-gray-900">Additional Details</h2>
              <span className="text-xs text-gray-400 font-medium ml-auto">Optional</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                  <CreditCard size={14} />
                  PAN (First 5 characters)
                </label>
                <input
                  type="text"
                  value={panFirst5}
                  onChange={(e) => setPanFirst5(e.target.value.toUpperCase().slice(0, 5))}
                  placeholder="e.g., ABCDE"
                  maxLength={5}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none uppercase"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                  <Phone size={14} />
                  Mobile (Last 5 digits)
                </label>
                <input
                  type="text"
                  value={mobileLast5}
                  onChange={(e) => setMobileLast5(e.target.value.replace(/\D/g, '').slice(0, 5))}
                  placeholder="e.g., 56789"
                  maxLength={5}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Required for SBI account statement passwords
                </p>
              </div>
            </div>
          </div>

          {/* Customer IDs */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-1">
              <CreditCard size={18} className="text-indigo-600" />
              <h2 className="text-base font-semibold text-gray-900">Bank Customer IDs</h2>
              <span className="text-xs text-gray-400 font-medium ml-auto">Optional</span>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              Some banks use Customer ID / CRN / CIF as the PDF password. Enter only for banks
              where you receive PDF statements.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {['HDFC', 'Kotak', 'Yes Bank', 'PNB', 'Canara'].map((bank) => (
                <div key={bank}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{bank}</label>
                  <input
                    type="text"
                    value={customerIds[bank] || ''}
                    onChange={(e) => handleCustomerIdChange(bank, e.target.value)}
                    placeholder={`${bank} Customer ID`}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Password patterns reference */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowBankInfo(!showBankInfo)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Info size={16} className="text-blue-500" />
                <span className="text-sm font-medium text-gray-700">
                  Bank PDF Password Patterns Reference
                </span>
              </div>
              {showBankInfo ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {showBankInfo && (
              <div className="px-4 pb-4 space-y-2">
                {Object.entries(BANK_PASSWORD_INFO).map(([bank, info]) => (
                  <div key={bank} className="flex gap-2 text-xs">
                    <span className="font-semibold text-gray-700 min-w-[80px]">{bank}:</span>
                    <span className="text-gray-500">{info}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            {isFirstTime && (
              <button
                type="button"
                onClick={handleSkip}
                className="px-6 py-3 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Skip for now
              </button>
            )}
            <button
              type="submit"
              disabled={saveMutation.isPending || !firstName.trim() || !dob}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saveMutation.isPending ? (
                <LoadingSpinner size={18} />
              ) : (
                <>
                  {isFirstTime ? (
                    <>
                      Save & Continue
                      <ArrowRight size={16} />
                    </>
                  ) : (
                    <>
                      <Check size={16} />
                      Save Profile
                    </>
                  )}
                </>
              )}
            </button>
          </div>

          {saveMutation.isError && (
            <p className="text-sm text-red-500 text-center">
              Failed to save profile. Please try again.
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
