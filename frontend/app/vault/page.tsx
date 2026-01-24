"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileUpload } from "@/components/file-upload";
import { uploadResume, type AtomicUnit, type MasterResumeResponse } from "@/lib/api";

export default function VaultPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MasterResumeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await uploadResume(file);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process resume");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <Link href="/" className="text-blue-600 hover:underline text-sm mb-2 inline-block">
          &larr; Back to Home
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Master Resume Vault
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          Upload your resume to extract verifiable atomic units of experience.
        </p>
      </div>

      {/* Upload Section */}
      {!result && (
        <Card className="max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle>Upload Your Resume</CardTitle>
            <CardDescription>
              We&apos;ll extract every bullet point as a verified &quot;atomic unit&quot; that can be
              used in tailored resumes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload onFileSelect={handleFileSelect} isLoading={isLoading} />
            {error && (
              <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-300">
                <AlertCircle className="w-5 h-5" />
                {error}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Success Banner */}
          <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <div>
                  <h3 className="font-semibold text-green-800 dark:text-green-200">
                    Resume Processed Successfully
                  </h3>
                  <p className="text-green-700 dark:text-green-300 text-sm">
                    Version: {result.master_version_id} | {result.atomic_units.length} atomic units extracted
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
              <CardContent className="pt-6">
                <h4 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
                  Warnings
                </h4>
                <ul className="list-disc list-inside text-yellow-700 dark:text-yellow-300 text-sm">
                  {result.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Counts Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Extraction Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(result.counts).map(([section, count]) => (
                  <div key={section} className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{count}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-300 capitalize">{section}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Atomic Units */}
          <Card>
            <CardHeader>
              <CardTitle>Extracted Atomic Units</CardTitle>
              <CardDescription>
                Review and edit your experience bullets. Each one can be used in tailored resumes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {result.atomic_units.map((unit) => (
                  <AtomicUnitCard key={unit.id} unit={unit} />
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Next Step */}
          <div className="flex justify-center">
            <Link href={`/compile?version=${result.master_version_id}`}>
              <Button size="lg" className="gap-2">
                Continue to Compile
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function AtomicUnitCard({ unit }: { unit: AtomicUnit }) {
  const sectionColors: Record<string, string> = {
    experience: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    projects: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    education: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    skills: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    header: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  };

  return (
    <div className="p-4 border rounded-lg hover:border-blue-300 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${sectionColors[unit.section] || sectionColors.experience}`}>
            {unit.section}
          </span>
          {unit.org && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {unit.org}
            </span>
          )}
          {unit.role && (
            <span className="text-sm text-gray-500">• {unit.role}</span>
          )}
        </div>
        <span className="text-xs text-gray-400 font-mono">{unit.id}</span>
      </div>
      <p className="text-gray-800 dark:text-gray-200">{unit.text}</p>
      {unit.tags.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {unit.tags.skills.slice(0, 5).map((skill) => (
            <span
              key={skill}
              className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-300"
            >
              {skill}
            </span>
          ))}
          {unit.tags.skills.length > 5 && (
            <span className="text-xs text-gray-500">+{unit.tags.skills.length - 5} more</span>
          )}
        </div>
      )}
    </div>
  );
}
