import { useState, useEffect } from 'react';
import { privacyApi } from '@/lib/api';
import type { PrivacySettings } from '@/types';

export function PrivacySettingsPanel() {
  const [settings, setSettings] = useState<PrivacySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await privacyApi.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load privacy settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateMasterToggle = async (enabled: boolean) => {
    if (!settings) return;
    setUpdating(true);
    try {
      const updated = await privacyApi.updateSettings({
        obfuscation_enabled: enabled,
      });
      setSettings(updated);
    } catch (error) {
      console.error('Failed to update settings:', error);
    } finally {
      setUpdating(false);
    }
  };

  const updateProviderSetting = async (provider: string, enabled: boolean) => {
    if (!settings) return;
    setUpdating(true);

    const newProviderSettings = settings.provider_settings.map(ps =>
      ps.provider === provider ? { ...ps, obfuscation_enabled: enabled } : ps
    );

    try {
      const updated = await privacyApi.updateSettings({
        provider_settings: newProviderSettings,
      });
      setSettings(updated);
    } catch (error) {
      console.error('Failed to update settings:', error);
    } finally {
      setUpdating(false);
    }
  };

  if (loading || !settings) {
    return (
      <div className="border rounded-lg p-4">
        <h2 className="text-lg font-semibold">Privacy Settings</h2>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4 space-y-6">
      <h2 className="text-lg font-semibold">Privacy Settings</h2>
      <p className="text-sm text-gray-600 mb-4">
        Control how your data is anonymized before sending to AI providers
      </p>

      {/* Master Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <label htmlFor="obfuscation-master" className="block text-base font-medium">
            Data Obfuscation
          </label>
          <p className="text-sm text-gray-600">
            Anonymize merchant names and dates before sending to AI
          </p>
        </div>
        <input
          id="obfuscation-master"
          type="checkbox"
          checked={settings.obfuscation_enabled}
          onChange={(e) => updateMasterToggle(e.target.checked)}
          disabled={updating}
          className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      </div>

      {/* Per-Provider Settings */}
      {settings.obfuscation_enabled && (
        <div className="space-y-4 pt-4 border-t">
          <h4 className="font-medium">Provider Settings</h4>
          <p className="text-sm text-gray-600">
            Configure obfuscation per provider. Local providers (Ollama) typically don't need obfuscation since data never leaves your machine.
          </p>
          {settings.provider_settings.map((ps) => (
            <div key={ps.provider} className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <span className="capitalize font-medium">{ps.provider}</span>
                {ps.provider === 'ollama' ? (
                  <span className="text-xs bg-gray-200 px-2 py-1 rounded">Local</span>
                ) : (
                  <span className="text-xs bg-blue-100 px-2 py-1 rounded">Cloud</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">
                  {ps.obfuscation_enabled ? 'Protected' : 'Raw data'}
                </span>
                <input
                  type="checkbox"
                  checked={ps.obfuscation_enabled}
                  onChange={(e) => updateProviderSetting(ps.provider, e.target.checked)}
                  disabled={updating}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Token Statistics */}
      <div className="space-y-3 pt-4 border-t">
        <h4 className="font-medium">Token Statistics</h4>
        <p className="text-sm text-gray-600">
          Tokens are anonymized identifiers that replace your actual data when sending to AI.
        </p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Merchants tokenized:</span>
            <span className="font-medium">{settings.stats.merchants}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Accounts tokenized:</span>
            <span className="font-medium">{settings.stats.accounts}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">People tokenized:</span>
            <span className="font-medium">{settings.stats.people}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Date shift:</span>
            <span className="font-medium">+{settings.stats.date_shift_days} days</span>
          </div>
        </div>
      </div>

      {/* Preview Example */}
      <div className="space-y-2 rounded-lg bg-gray-50 p-4 border">
        <h4 className="font-medium text-sm">What AI Sees (Example)</h4>
        <div className="font-mono text-sm bg-white rounded p-2 border">
          MERCHANT_042 [Groceries] $187.34 2026-08-09
        </div>
        <p className="text-xs text-gray-600">
          Your actual merchant names, dates, and accounts are replaced with anonymous tokens.
          The AI can still understand patterns and provide insights without knowing your specific data.
        </p>
      </div>
    </div>
  );
}
