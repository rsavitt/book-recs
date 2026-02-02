"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { UserProfile } from "@/types";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Privacy settings
  const [isPublic, setIsPublic] = useState(false);
  const [allowDataForRecs, setAllowDataForRecs] = useState(true);
  const [savingPrivacy, setSavingPrivacy] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      const data = await api.getProfile();
      setProfile(data);
      setIsPublic(data.is_public);
    } catch (err) {
      if (err instanceof Error && err.message.includes("401")) {
        router.push("/login");
        return;
      }
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleSavePrivacy = async () => {
    setSavingPrivacy(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/account/privacy`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${api.getToken()}`,
        },
        body: JSON.stringify({
          is_public: isPublic,
          allow_data_for_recs: allowDataForRecs,
        }),
      });
    } catch {
      setError("Failed to save privacy settings");
    } finally {
      setSavingPrivacy(false);
    }
  };

  const handleExportData = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/account/export`, {
        headers: {
          Authorization: `Bearer ${api.getToken()}`,
        },
      });
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${profile?.username || "user"}_data_export.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to export data");
    }
  };

  const handleLogout = () => {
    api.logout();
    router.push("/");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Failed to load profile</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="font-semibold text-xl text-gray-900">Romantasy Recs</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/recommendations" className="text-gray-600 hover:text-gray-900">
              Recommendations
            </Link>
            <button onClick={handleLogout} className="text-gray-600 hover:text-gray-900">
              Log out
            </button>
          </div>
        </nav>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Profile Header */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">👤</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {profile.display_name || profile.username}
              </h1>
              <p className="text-gray-500">@{profile.username}</p>
            </div>
          </div>

          {profile.bio && <p className="mt-4 text-gray-600">{profile.bio}</p>}
        </div>

        {/* Reading Stats */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Reading Stats</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{profile.stats.total_books}</div>
              <div className="text-sm text-gray-500">Books</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{profile.stats.total_rated}</div>
              <div className="text-sm text-gray-500">Rated</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {profile.stats.average_rating.toFixed(1)}
              </div>
              <div className="text-sm text-gray-500">Avg Rating</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {profile.top_shelves.length}
              </div>
              <div className="text-sm text-gray-500">Shelves</div>
            </div>
          </div>

          {/* Rating Distribution */}
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Rating Distribution</h3>
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((rating) => {
                const count = profile.stats.rating_distribution[rating] || 0;
                const maxCount = Math.max(...Object.values(profile.stats.rating_distribution));
                const width = maxCount > 0 ? (count / maxCount) * 100 : 0;

                return (
                  <div key={rating} className="flex items-center gap-2">
                    <div className="w-8 text-sm text-gray-600">{rating}★</div>
                    <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full transition-all"
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <div className="w-8 text-sm text-gray-500 text-right">{count}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Preferences</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500">Spice Preference</span>
              <div className="font-medium">
                {profile.spice_preference !== null
                  ? "🌶️".repeat(profile.spice_preference) || "None"
                  : "Not set"}
              </div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Age Category</span>
              <div className="font-medium">
                {profile.prefers_ya === true && "YA"}
                {profile.prefers_ya === false && "Adult"}
                {profile.prefers_ya === null && "Both"}
              </div>
            </div>
          </div>
        </div>

        {/* Privacy Settings */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Privacy Settings</h2>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium">Public Profile</div>
                <div className="text-sm text-gray-500">
                  Allow other users to see your profile and reading stats
                </div>
              </div>
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="w-5 h-5 text-purple-600 rounded"
              />
            </label>

            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium">Contribute to Recommendations</div>
                <div className="text-sm text-gray-500">
                  Allow your ratings to help recommend books to similar readers
                </div>
              </div>
              <input
                type="checkbox"
                checked={allowDataForRecs}
                onChange={(e) => setAllowDataForRecs(e.target.checked)}
                className="w-5 h-5 text-purple-600 rounded"
              />
            </label>

            <button
              onClick={handleSavePrivacy}
              disabled={savingPrivacy}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
            >
              {savingPrivacy ? "Saving..." : "Save Privacy Settings"}
            </button>
          </div>
        </div>

        {/* Account Actions */}
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Account</h2>
          <div className="space-y-3">
            <button
              onClick={handleExportData}
              className="w-full text-left px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="font-medium">Export My Data</div>
              <div className="text-sm text-gray-500">Download all your data as JSON</div>
            </button>

            <button className="w-full text-left px-4 py-3 border border-red-200 rounded-lg hover:bg-red-50 text-red-600">
              <div className="font-medium">Delete Account</div>
              <div className="text-sm text-red-400">Permanently delete your account and data</div>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
