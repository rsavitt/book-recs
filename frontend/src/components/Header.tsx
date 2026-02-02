"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface HeaderProps {
  showAuthButtons?: boolean;
}

export function Header({ showAuthButtons = true }: HeaderProps) {
  const pathname = usePathname();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Check auth status after hydration to avoid SSR mismatch
  useEffect(() => {
    setIsLoggedIn(!!api.getToken());
  }, []);

  const isActive = (path: string) => pathname === path;

  return (
    <header className="bg-white shadow-sm sticky top-0 z-10">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-2xl">📚</span>
          <span className="font-semibold text-xl text-gray-900">Romantasy Recs</span>
        </Link>

        <div className="flex items-center gap-4">
          <Link
            href="/browse"
            className={`text-sm ${
              isActive("/browse")
                ? "text-purple-600 font-medium"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Browse
          </Link>

          {isLoggedIn ? (
            <>
              <Link
                href="/recommendations"
                className={`text-sm ${
                  isActive("/recommendations")
                    ? "text-purple-600 font-medium"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                My Recs
              </Link>
              <Link
                href="/similar-readers"
                className={`text-sm ${
                  isActive("/similar-readers")
                    ? "text-purple-600 font-medium"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Similar Readers
              </Link>
              <Link
                href="/profile"
                className={`text-sm ${
                  isActive("/profile")
                    ? "text-purple-600 font-medium"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Profile
              </Link>
            </>
          ) : showAuthButtons ? (
            <>
              <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">
                Log in
              </Link>
              <Link
                href="/register"
                className="text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
              >
                Get Started
              </Link>
            </>
          ) : null}
        </div>
      </nav>
    </header>
  );
}
