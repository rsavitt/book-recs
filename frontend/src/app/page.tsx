import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="font-semibold text-xl text-gray-900">Romantasy Recs</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <main>
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl sm:text-6xl font-bold text-gray-900 tracking-tight">
              Find Your Next Favorite
              <span className="block text-purple-600">Romantasy</span>
            </h1>
            <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
              Import your Goodreads library and discover Romantasy books loved by readers with similar tastes.
              No more endless scrolling—just personalized recommendations.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/register"
                className="bg-purple-600 text-white px-8 py-4 rounded-lg text-lg font-medium hover:bg-purple-700 transition-colors"
              >
                Import Your Library
              </Link>
              <Link
                href="/browse"
                className="bg-white text-gray-700 px-8 py-4 rounded-lg text-lg font-medium border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                Browse Romantasy
              </Link>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="bg-white py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
              How It Works
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">📤</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  1. Import Your Library
                </h3>
                <p className="text-gray-600">
                  Upload your Goodreads export CSV. We&apos;ll analyze your ratings and reading history.
                </p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🔍</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  2. Find Your People
                </h3>
                <p className="text-gray-600">
                  We match you with readers who share your taste. See who else loved the same books.
                </p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">✨</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  3. Get Recommendations
                </h3>
                <p className="text-gray-600">
                  Discover Romantasy books that similar readers loved—with explanations for each pick.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
              Filter By What Matters
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <span className="text-2xl mb-3 block">🌶️</span>
                <h3 className="font-semibold text-gray-900">Spice Level</h3>
                <p className="text-sm text-gray-600 mt-1">
                  From fade-to-black to open door—find your comfort zone.
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <span className="text-2xl mb-3 block">🎭</span>
                <h3 className="font-semibold text-gray-900">Tropes</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Enemies-to-lovers, forced proximity, fae courts, and more.
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <span className="text-2xl mb-3 block">📖</span>
                <h3 className="font-semibold text-gray-900">YA or Adult</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Choose your preferred age category or see both.
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <span className="text-2xl mb-3 block">📚</span>
                <h3 className="font-semibold text-gray-900">Series Status</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Complete series, standalones, or ongoing—your choice.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="bg-purple-600 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Find Your Next Read?
            </h2>
            <p className="text-purple-100 mb-8 text-lg">
              Join readers who&apos;ve discovered their new favorite Romantasy books.
            </p>
            <Link
              href="/register"
              className="bg-white text-purple-600 px-8 py-4 rounded-lg text-lg font-medium hover:bg-purple-50 transition-colors inline-block"
            >
              Get Started Free
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm">
          <p>Built for Romantasy lovers. Your data stays private.</p>
        </div>
      </footer>
    </div>
  );
}
