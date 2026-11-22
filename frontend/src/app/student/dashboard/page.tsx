'use client'

import { useState } from 'react'
import Link from 'next/link'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { apiFetch } from '@/lib/api'
import { Award, Clock, Upload, CheckCircle2, X, Loader2 } from 'lucide-react'

type DashboardAssignment = {
  id: string
  title: string
  course: string
  dueDate: string
}

export default function StudentDashboard() {
  const enrolledCourses = [
    { id: '1', title: 'Python Programming Masterclass', instructor: 'Dr. Sarah Ahmed', progress: 75, nextLesson: 'Variables & Data Types' },
    { id: '2', title: 'Full-Stack Web Development with Next.js', instructor: 'Eng. Layla Omar', progress: 40, nextLesson: 'App Router Architecture' },
  ]

  const upcomingAssignments = [
    { id: 'a1', title: 'Assignment 1: Build a Python Calculator', course: 'Python Programming Masterclass', dueDate: 'Nov 25, 2026' },
    { id: 'a2', title: 'React State Management Project', course: 'Full-Stack Web Development', dueDate: 'Nov 28, 2026' },
  ]

  const [selectedAssignment, setSelectedAssignment] = useState<DashboardAssignment | null>(null)
  const [submissionText, setSubmissionText] = useState('')
  const [fileUrl, setFileUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleOpenSubmitModal = (assignment: DashboardAssignment) => {
    setSelectedAssignment(assignment)
    setSubmissionText('')
    setFileUrl('')
    setError(null)
    setSuccessMessage(null)
  }

  const handleSubmitAssignment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAssignment) return
    setSubmitting(true)
    setError(null)

    try {
      await apiFetch(`/assignments/${selectedAssignment.id}/submit`, {
        method: 'POST',
        body: JSON.stringify({
          file_url: fileUrl || null,
          submission_text: submissionText || null,
        }),
      })

      setSuccessMessage('Assignment submitted successfully! Your teacher can now review and grade it.')
      setTimeout(() => {
        setSelectedAssignment(null)
        setSuccessMessage(null)
      }, 2500)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to submit the assignment.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Canvas Global Navigation Sidebar */}
      <CanvasSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-slate-900">Basira — Student Dashboard</span>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
          {/* Welcome Banner */}
          <div className="bg-indigo-700 text-white rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold">Welcome back, Student!</h1>
              <p className="text-indigo-200 mt-1">Keep track of your enrolled courses and submit your assignments on time.</p>
            </div>
            <div className="bg-indigo-600/50 backdrop-blur px-4 py-3 rounded-xl border border-indigo-500 flex items-center gap-3">
              <Award className="w-8 h-8 text-amber-300" />
              <div>
                <p className="text-xs text-indigo-200">Overall Progress</p>
                <p className="text-lg font-bold">68% Completed</p>
              </div>
            </div>
          </div>

          {/* Enrolled Courses Grid */}
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-4">Enrolled Courses</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {enrolledCourses.map((course) => (
                <div key={course.id} className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col justify-between">
                  <div>
                    <h3 className="font-semibold text-lg text-slate-900">{course.title}</h3>
                    <p className="text-xs text-slate-500 mt-1">Instructor: {course.instructor}</p>
                    <div className="mt-4">
                      <div className="flex justify-between text-xs font-medium text-slate-600 mb-1">
                        <span>Progress</span>
                        <span>{course.progress}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div className="bg-indigo-600 h-2 rounded-full" style={{ width: `${course.progress}%` }}></div>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600 mt-4 flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-indigo-600" />
                      <span>Next: {course.nextLesson}</span>
                    </p>
                  </div>
                  <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
                    <Link
                      href={`/student/courses/${course.id}`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Continue Course &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Assignments with Submit Button */}
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-4">Upcoming Assignments</h2>
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100">
              {upcomingAssignments.map((assignment) => (
                <div key={assignment.id} className="p-4 sm:px-6 flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-slate-900">{assignment.title}</h4>
                    <p className="text-xs text-slate-500">{assignment.course}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs font-medium bg-amber-50 text-amber-700 px-3 py-1 rounded-full border border-amber-200">
                      Due {assignment.dueDate}
                    </span>
                    <button
                      onClick={() => handleOpenSubmitModal(assignment)}
                      className="text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-2 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>Submit Work</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      {/* Assignment Submission Modal */}
      {selectedAssignment && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Submit Assignment</h3>
                <p className="text-xs text-slate-500">{selectedAssignment.title} ({selectedAssignment.course})</p>
              </div>
              <button
                onClick={() => setSelectedAssignment(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {successMessage ? (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl flex items-center gap-3 text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>{successMessage}</span>
              </div>
            ) : (
              <form onSubmit={handleSubmitAssignment} className="space-y-4">
                {error && (
                  <div className="bg-red-50 text-red-700 p-3 rounded-lg text-xs">{error}</div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Submission File URL / GitHub Link</label>
                  <input
                    type="url"
                    value={fileUrl}
                    onChange={(e) => setFileUrl(e.target.value)}
                    placeholder="https://github.com/my-repo/assignment"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Or Text / Code Answer</label>
                  <textarea
                    rows={4}
                    value={submissionText}
                    onChange={(e) => setSubmissionText(e.target.value)}
                    placeholder="Paste your code or written response here..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  ></textarea>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setSelectedAssignment(null)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || (!fileUrl && !submissionText)}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    <span>Submit to Teacher</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* AI Assistant Widget */}
      <AIAssistantWidget userRole="student" />
    </div>
  )
}
