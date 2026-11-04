// app/schemes/page.tsx
"use client";

import { useState } from "react";
import Image from "next/image";
import {
  Plus,
  Search,
  Filter,
  FileText,
  Users,
  CheckCircle,
  X,
} from "lucide-react";

type Scheme = {
  id: string;
  title: string;
  description: string;
  benefits: string;
  required_documents: string[];
  target_states: string[]; // ✅ ONLY filter
  is_active: boolean;
  created_at: string;
};

// Add Indian states list
const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];

export default function SchemesPage() {
  const [view, setView] = useState<"list" | "create" | "applications">("list");
  const [selectedScheme, setSelectedScheme] = useState<Scheme | null>(null);
  const [schemes, setSchemes] = useState<Scheme[]>([]);

  return (
    <div className="flex min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex h-16 items-center border-b border-zinc-200 px-6 dark:border-zinc-800">
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Scheme Manager
          </h1>
        </div>
        <nav className="space-y-1 p-4">
          <button
            onClick={() => setView("list")}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              view === "list"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/50"
            }`}
          >
            <FileText className="h-4 w-4" />
            All Schemes
          </button>
          <button
            onClick={() => setView("create")}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              view === "create"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/50"
            }`}
          >
            <Plus className="h-4 w-4" />
            Create Scheme
          </button>
          <button
            onClick={() => setView("applications")}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              view === "applications"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/50"
            }`}
          >
            <Users className="h-4 w-4" />
            Applications
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1">
        {view === "list" && (
          <SchemesList schemes={schemes} onSelect={setSelectedScheme} />
        )}
        {view === "create" && (
          <CreateScheme onSuccess={() => setView("list")} />
        )}
        {view === "applications" && <ApplicationsList />}
      </main>
    </div>
  );
}

// Components

function SchemesList({
  schemes,
  onSelect,
}: {
  schemes: Scheme[];
  onSelect: (s: Scheme) => void;
}) {
  const [search, setSearch] = useState("");

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          All Schemes
        </h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search schemes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-64 rounded-lg border border-zinc-200 bg-white pl-10 pr-4 text-sm focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          />
        </div>
      </div>

      <div className="grid gap-4">
        {schemes.map((scheme) => (
          <div
            key={scheme.id}
            onClick={() => onSelect(scheme)}
            className="cursor-pointer rounded-lg border border-zinc-200 bg-white p-6 transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  {scheme.title}
                </h3>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  {scheme.description}
                </p>
                <div className="mt-4 flex items-center gap-4">
                  <span className="text-xs text-zinc-500 dark:text-zinc-500">
                    {scheme.required_documents.length} documents required
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CreateScheme({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    benefits: "",
    required_documents: [""],
    target_states: [] as string[], // ✅ Added target_states
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch("/api/schemes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        onSuccess();
      }
    } catch (error) {
      console.error("Failed to create scheme:", error);
    }
  };

  const addDocumentField = () => {
    setFormData({
      ...formData,
      required_documents: [...formData.required_documents, ""],
    });
  };

  const updateDocument = (index: number, value: string) => {
    const newDocs = [...formData.required_documents];
    newDocs[index] = value;
    setFormData({ ...formData, required_documents: newDocs });
  };

  const removeDocument = (index: number) => {
    setFormData({
      ...formData,
      required_documents: formData.required_documents.filter(
        (_, i) => i !== index,
      ),
    });
  };

  // ✅ Handle state selection
  const toggleState = (state: string) => {
    setFormData((prev) => ({
      ...prev,
      target_states: prev.target_states.includes(state)
        ? prev.target_states.filter((s) => s !== state)
        : [...prev.target_states, state],
    }));
  };

  const selectAllStates = () => {
    setFormData((prev) => ({
      ...prev,
      target_states: [...INDIAN_STATES],
    }));
  };

  const clearAllStates = () => {
    setFormData((prev) => ({
      ...prev,
      target_states: [],
    }));
  };

  return (
    <div className="p-8">
      <h2 className="mb-6 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        Create New Scheme
      </h2>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-900 dark:text-zinc-50">
            Scheme Title
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) =>
              setFormData({ ...formData, title: e.target.value })
            }
            className="w-full rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            required
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-900 dark:text-zinc-50">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) =>
              setFormData({ ...formData, description: e.target.value })
            }
            rows={4}
            className="w-full rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            required
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-900 dark:text-zinc-50">
            Benefits
          </label>
          <textarea
            value={formData.benefits}
            onChange={(e) =>
              setFormData({ ...formData, benefits: e.target.value })
            }
            rows={3}
            className="w-full rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            required
          />
        </div>

        {/* ✅ Target States Selection */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-50">
              Target States ({formData.target_states.length} selected)
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={selectAllStates}
                className="text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
              >
                Select All
              </button>
              <button
                type="button"
                onClick={clearAllStates}
                className="text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
              >
                Clear All
              </button>
            </div>
          </div>

          {/* Selected States Pills */}
          {formData.target_states.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {formData.target_states.map((state) => (
                <span
                  key={state}
                  className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  {state}
                  <button
                    type="button"
                    onClick={() => toggleState(state)}
                    className="hover:text-zinc-900 dark:hover:text-zinc-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* States Grid */}
          <div className="max-h-48 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
            <div className="grid grid-cols-2 gap-2">
              {INDIAN_STATES.map((state) => (
                <label
                  key={state}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={formData.target_states.includes(state)}
                    onChange={() => toggleState(state)}
                    className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500 dark:border-zinc-600 dark:bg-zinc-800"
                  />
                  <span className="text-sm text-zinc-900 dark:text-zinc-50">
                    {state}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-900 dark:text-zinc-50">
            Required Documents
          </label>
          <div className="space-y-2">
            {formData.required_documents.map((doc, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  value={doc}
                  onChange={(e) => updateDocument(index, e.target.value)}
                  placeholder="e.g., Aadhar Card"
                  className="flex-1 rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                  required
                />
                {formData.required_documents.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeDocument(index)}
                    className="rounded-lg border border-zinc-200 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:border-zinc-700 dark:hover:bg-red-900/20"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addDocumentField}
              className="flex items-center gap-2 text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
            >
              <Plus className="h-4 w-4" />
              Add Document
            </button>
          </div>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Create Scheme
          </button>
        </div>
      </form>
    </div>
  );
}

function ApplicationsList() {
  const [filters, setFilters] = useState({
    status: "all",
    state: "all", // ✅ Added state filter
    landSize: "",
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [applications, setApplications] = useState<any[]>([]);

  const handleApprove = async (id: string) => {
    try {
      await fetch(`/api/applications/${id}/approve`, {
        method: "POST",
      });
      // Refresh applications list
    } catch (error) {
      console.error("Failed to approve:", error);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await fetch(`/api/applications/${id}/reject`, {
        method: "POST",
      });
      // Refresh applications list
    } catch (error) {
      console.error("Failed to reject:", error);
    }
  };

  return (
    <div className="p-8">
      <h2 className="mb-6 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        Farmer Applications
      </h2>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-4">
        {/* Status Filter */}
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>

        {/* ✅ State Filter */}
        <select
          value={filters.state}
          onChange={(e) => setFilters({ ...filters, state: e.target.value })}
          className="rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          <option value="all">All States</option>
          {INDIAN_STATES.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>

        {/* Land Size Filter */}
        <input
          type="number"
          placeholder="Min land size (acres)..."
          value={filters.landSize}
          onChange={(e) => setFilters({ ...filters, landSize: e.target.value })}
          className="rounded-lg border border-zinc-200 bg-white px-4 py-2 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
      </div>

      {/* Applications Grid */}
      <div className="grid gap-4">
        {applications.map((app) => (
          <div
            key={app.id}
            className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">
                  {app.farmer.name}
                </h3>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  {app.farmer.state} • {app.farmer.land_size} acres
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      app.status === "pending"
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400"
                        : app.status === "approved"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                    }`}
                  >
                    {app.status}
                  </span>
                </div>
              </div>

              {app.status === "pending" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(app.id)}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(app.id)}
                    className="rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
