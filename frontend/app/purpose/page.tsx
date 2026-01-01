'use client'

import { useRouter } from 'next/navigation'

export default function PurposePage() {
  const router = useRouter()

  return (
    <main className="min-h-screen bg-sky-100 text-slate-900 page-fade-in">
      <div className="max-w-3xl mx-auto px-8 py-16">
        <button
          onClick={() => router.push('/')}
          className="text-slate-700 hover:text-slate-900 mb-8 flex items-center space-x-2 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Home</span>
        </button>

        <div className="bg-white border border-slate-200 rounded-3xl p-10 shadow-sm">
          <h1 className="text-4xl md:text-5xl font-semibold text-slate-900 mb-6">
            Why I Built Lectora
          </h1>
          <div className="space-y-5 text-lg text-slate-700 leading-relaxed">
            <p>Education should be a fundamental right.</p>
            <p>However, a lot of the time it does not feel that way.</p>
            <p>
              In the US, college keeps getting more and more expensive. Textbooks are
              literally hundreds of dollars, and a lot of basic learning material is
              still stuck behind paywalls. Before you even start learning, you are
              already thinking about money.
            </p>
            <p>
              Fortunately, places like MIT OCW and a bunch of professors from different
              universities upload their lecture slides publicly, which is honestly
              great. But the problem is that a lot of these slides are basically
              unreadable unless you were actually in the lecture or had access to the
              recording, and most of the time, you do not.
            </p>
            <p>
              That is kind of the whole point of this app: to take all that stuff that
              is already out there and make this shit intelligible.
            </p>
            <p>
              I do not want this to replace professors. Real teaching matters. Real
              classrooms matter. But if someone cannot get into that class, or cannot
              afford it, or just missed something, they should not be screwed because
              of that.
            </p>
            <p>If the knowledge is already out there, it should actually be usable.</p>
            <p>
              I built this because I have literally been in that spot: staring at
              slides, stressed before an exam, and feeling like the entire lecture was
              hidden somewhere I could not access. And honestly, that should not be
              normal.
            </p>
            <p>This app is just my small attempt to fix a tiny piece of that problem.</p>
            <p>Make things clearer. Fill in the gaps.</p>
            <p>
              Let people actually learn without needing money or access to some fancy
              school.
            </p>
            <p>
              If this helps even a few people understand something they otherwise
              would not have, that is enough for me.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
