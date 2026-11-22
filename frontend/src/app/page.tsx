import Link from 'next/link'
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  GraduationCap,
  Play,
  Sparkles,
} from 'lucide-react'

const highlights = [
  {
    icon: BookOpen,
    title: 'Learn at your pace',
    description: 'Follow structured lessons, revisit materials, and pick up right where you left off.',
  },
  {
    icon: BrainCircuit,
    title: 'Get help as you learn',
    description: 'Ask the course assistant questions about the lesson you are currently studying.',
  },
  {
    icon: CheckCircle2,
    title: 'See your progress',
    description: 'Keep courses, upcoming assignments, and learning progress together in one place.',
  },
]

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3" aria-label="Basira home">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-200">
              <BookOpen className="h-6 w-6" />
            </span>
            <span className="text-xl font-bold tracking-tight">Basira</span>
          </Link>
          <nav className="flex items-center gap-3 sm:gap-6" aria-label="Main navigation">
            <Link href="/login" className="text-sm font-semibold text-slate-600 transition hover:text-indigo-600">
              Sign in
            </Link>
            <Link
              href="/signup"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
            >
              Create account
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="relative isolate overflow-hidden bg-slate-50">
          <div className="pointer-events-none absolute -right-32 -top-32 -z-10 h-96 w-96 rounded-full bg-indigo-200/50 blur-3xl" />
          <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white px-3.5 py-2 text-xs font-semibold text-indigo-700 shadow-sm">
                <Sparkles className="h-4 w-4" />
                A clearer way to learn online
              </div>
              <h1 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
                Make every lesson a{' '}
                <span className="text-indigo-600">step forward.</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
                Basira brings courses, assignments, and an AI learning companion into one focused space for students and educators.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 font-semibold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:bg-indigo-700"
                >
                  <Play className="h-4 w-4" />
                  Sign in to your workspace
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3.5 font-semibold text-slate-800 transition hover:border-indigo-300 hover:bg-indigo-50"
                >
                  Get started
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                Create a student account to get started. Teacher accounts are invited by an administrator.
              </p>
            </div>

            <div className="relative">
              <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-indigo-100 to-sky-100 blur-xl" />
              <div className="relative rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl shadow-slate-300/50 sm:p-7">
                <div className="flex items-center justify-between border-b border-slate-100 pb-5">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                      <GraduationCap className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-sm font-bold">Student workspace preview</p>
                      <p className="text-xs text-slate-500">A little progress, every day</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600">Sample content</span>
                </div>

                <div className="mt-5 rounded-2xl bg-indigo-600 p-5 text-white">
                  <p className="text-xs font-medium text-indigo-200">CONTINUE LEARNING</p>
                  <h2 className="mt-2 text-lg font-bold">Introduction to Computer Science</h2>
                  <div className="mt-5 flex items-center justify-between text-xs text-indigo-100">
                    <span>Course progress</span>
                    <span>75%</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-indigo-400/50">
                    <div className="h-2 w-3/4 rounded-full bg-white" />
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Next lesson</p>
                    <p className="mt-2 text-sm font-semibold">Algorithms &amp; Data Structures</p>
                    <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-indigo-600">
                      <Play className="h-3.5 w-3.5" /> 12 min
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="flex items-center gap-1.5 text-xs font-medium text-indigo-600">
                      <Sparkles className="h-3.5 w-3.5" /> BASIRA AI
                    </p>
                    <p className="mt-2 text-sm font-semibold">Questions are part of learning.</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">Get guidance while you study.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-bold uppercase tracking-widest text-indigo-600">One connected experience</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Built around the way people learn</h2>
            <p className="mt-4 leading-7 text-slate-600">A focused learning workflow that helps students stay organized and teachers support their classes.</p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {highlights.map(({ icon: Icon, title, description }) => (
              <article key={title} className="rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg hover:shadow-slate-200/70">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="mt-5 text-lg font-bold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-slate-50">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-7 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="font-semibold text-slate-700">Basira</span>
          <span>Learning with clarity, one step at a time.</span>
        </div>
      </footer>
    </div>
  )
}
