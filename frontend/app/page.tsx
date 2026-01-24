"use client";

import Link from "next/link";
import { FileText, Target, Download, CheckCircle } from "lucide-react";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center px-6 py-24 text-center bg-gradient-to-b from-blue-50 to-white dark:from-gray-900 dark:to-gray-950">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
          Resume.<span className="text-blue-600">compile</span>()
        </h1>
        <p className="mt-6 text-xl text-gray-600 dark:text-gray-300 max-w-2xl">
          Truth-first resume tailoring. Zero hallucinations. Every bullet traces back to your verified experience.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/vault"
            className="rounded-lg bg-blue-600 px-6 py-3 text-lg font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Get Started
          </Link>
          <Link
            href="#how-it-works"
            className="rounded-lg bg-white px-6 py-3 text-lg font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
          >
            Learn More
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 px-6">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-bold text-center mb-16 text-gray-900 dark:text-white">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="flex flex-col items-center text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
              <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-4">
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">1. Upload Your Resume</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Upload your master resume PDF. We extract every bullet point as a verified &quot;atomic unit&quot; of experience.
              </p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
              <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center mb-4">
                <Target className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">2. Paste Job Description</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Paste a job posting URL or text. Our AI extracts requirements and matches them to your experience.
              </p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
              <div className="w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center mb-4">
                <Download className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">3. Download Tailored PDF</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Review the AI-selected bullets, toggle any changes, and download a perfectly formatted PDF.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6 bg-gray-50 dark:bg-gray-900">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-bold text-center mb-16 text-gray-900 dark:text-white">
            Why Resume.compile()?
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <FeatureCard
              icon={<CheckCircle className="w-6 h-6 text-green-500" />}
              title="Zero Hallucinations"
              description="Every output bullet traces back to your original resume. Nothing is invented or fabricated."
            />
            <FeatureCard
              icon={<CheckCircle className="w-6 h-6 text-green-500" />}
              title="Full Provenance"
              description="See exactly why each bullet was selected and which job requirements it addresses."
            />
            <FeatureCard
              icon={<CheckCircle className="w-6 h-6 text-green-500" />}
              title="Smart Matching"
              description="AI scores your experience against job requirements to maximize relevance."
            />
            <FeatureCard
              icon={<CheckCircle className="w-6 h-6 text-green-500" />}
              title="One-Page Optimized"
              description="Automatically fits the best content into a clean, one-page format."
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 text-center">
        <h2 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">
          Ready to compile your perfect resume?
        </h2>
        <Link
          href="/vault"
          className="inline-block rounded-lg bg-blue-600 px-8 py-4 text-xl font-semibold text-white shadow-sm hover:bg-blue-500"
        >
          Start Now - It&apos;s Free
        </Link>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-gray-200 dark:border-gray-800">
        <div className="text-center text-gray-500 text-sm">
          Built for SwampHacks XI | Using Gemini API, MongoDB Atlas, DigitalOcean
        </div>
      </footer>
    </main>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-4 p-6 rounded-xl bg-white dark:bg-gray-800 shadow-sm">
      <div className="flex-shrink-0">{icon}</div>
      <div>
        <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
        <p className="text-gray-600 dark:text-gray-300 text-sm mt-1">{description}</p>
      </div>
    </div>
  );
}
