import React, { useEffect, useState } from 'react';
import {
  Check,
  CheckCircle2,
  Clock,
  Edit2,
  Mail,
  Send,
  ThumbsDown,
  ThumbsUp,
  UserCheck,
} from 'lucide-react';
import { OutreachDraft } from '../types';
import { approveOutreachDraft, getOutreachQueue, recordLeadFeedback } from '../services/api';

export const OutreachQueue: React.FC = () => {
  const [queue, setQueue] = useState<OutreachDraft[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<OutreachDraft | null>(null);
  const [editingDraft, setEditingDraft] = useState<OutreachDraft | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Feedback Calibration state
  const [feedbackLeadId, setFeedbackLeadId] = useState('lead-dhl-com');
  const [feedbackAccurate, setFeedbackAccurate] = useState(true);
  const [feedbackNotes, setFeedbackNotes] = useState('Strong operational fit with Strategy 2030 initiatives.');
  const [feedbackSaved, setFeedbackSaved] = useState(false);

  const fetchQueue = async () => {
    setIsLoading(true);
    try {
      const items = await getOutreachQueue();
      setQueue(items);
      if (items.length > 0 && !selectedDraft) {
        setSelectedDraft(items[0]);
      }
    } catch (err) {
      console.error('Fetch queue error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleApprove = async (draftId: string) => {
    try {
      await approveOutreachDraft(draftId);
      setActionSuccess(`Draft ${draftId} approved and dispatched successfully.`);
      setTimeout(() => setActionSuccess(null), 3000);
      setQueue(
        queue.map((d) =>
          d.draft_id === draftId ? { ...d, status: 'DISPATCHED' } : d
        )
      );
      if (selectedDraft?.draft_id === draftId) {
        setSelectedDraft({ ...selectedDraft, status: 'DISPATCHED' });
      }
    } catch (err) {
      alert('Approval failed: ' + (err as Error).message);
    }
  };

  const handleSaveEdit = () => {
    if (!editingDraft) return;
    setQueue(
      queue.map((d) => (d.draft_id === editingDraft.draft_id ? editingDraft : d))
    );
    setSelectedDraft(editingDraft);
    setEditingDraft(null);
  };

  const handleSubmitFeedback = async () => {
    try {
      await recordLeadFeedback(feedbackLeadId, feedbackAccurate, feedbackNotes);
      setFeedbackSaved(true);
      setTimeout(() => setFeedbackSaved(false), 3000);
    } catch (err) {
      alert('Feedback failed: ' + (err as Error).message);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <Mail className="w-5 h-5 text-orange-600" />
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Human-in-the-Loop (HitL) Outreach Queue
          </h1>
        </div>
        <p className="text-xs text-slate-500">
          Review, calibrate, and dispatch evidence-grounded sales communications. Automated safeguards ensure every outreach draft passes human review before external delivery.
        </p>
      </div>

      {actionSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-md text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Main Layout: List on Left, Inspector on Right */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Queue List */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-xs p-4 space-y-3">
          <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
            <span className="font-bold uppercase tracking-wider text-slate-700">
              Staged Drafts ({queue.length})
            </span>
            <button
              onClick={fetchQueue}
              className="text-orange-600 hover:underline font-semibold"
            >
              Refresh
            </button>
          </div>

          <div className="space-y-2">
            {queue.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center italic">
                No drafts currently staged in queue.
              </p>
            ) : (
              queue.map((item) => {
                const isSelected = selectedDraft?.draft_id === item.draft_id;
                const isApproved = item.status === 'DISPATCHED';

                return (
                  <div
                    key={item.draft_id}
                    onClick={() => {
                      setSelectedDraft(item);
                      setEditingDraft(null);
                    }}
                    className={`p-3 rounded border text-xs cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-orange-500 bg-orange-50/40'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-slate-900 truncate">
                        {item.company_name || 'Enterprise Account'}
                      </span>
                      {isApproved ? (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          Dispatched
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          <span>Review</span>
                        </span>
                      )}
                    </div>
                    <div className="text-slate-500 truncate text-[11px]">
                      {item.recipient}
                    </div>
                    <div className="text-slate-700 font-medium truncate mt-1">
                      {item.subject}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Draft Editor & Preview */}
        <div className="md:col-span-2 bg-white rounded-lg border border-slate-200 shadow-xs p-6 space-y-4">
          {selectedDraft ? (
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div>
                  <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">
                    Draft ID: {selectedDraft.draft_id}
                  </span>
                  <h2 className="text-base font-bold text-slate-900">
                    {selectedDraft.company_name || 'Outreach Preview'}
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  {!editingDraft ? (
                    <button
                      onClick={() => setEditingDraft({ ...selectedDraft })}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>Edit Draft</span>
                    </button>
                  ) : (
                    <button
                      onClick={handleSaveEdit}
                      className="px-3 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white"
                    >
                      Done Editing
                    </button>
                  )}

                  {selectedDraft.status === 'AWAITING_HUMAN_APPROVAL' && (
                    <button
                      onClick={() => handleApprove(selectedDraft.draft_id)}
                      className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold rounded bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve and Dispatch</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Form Fields */}
              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-500 font-semibold mb-1">
                    Target Recipient
                  </label>
                  {editingDraft ? (
                    <input
                      type="text"
                      value={editingDraft.recipient}
                      onChange={(e) =>
                        setEditingDraft({ ...editingDraft, recipient: e.target.value })
                      }
                      className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded font-mono"
                    />
                  ) : (
                    <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded font-mono text-slate-800">
                      {selectedDraft.recipient}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-slate-500 font-semibold mb-1">
                    Subject Line
                  </label>
                  {editingDraft ? (
                    <input
                      type="text"
                      value={editingDraft.subject}
                      onChange={(e) =>
                        setEditingDraft({ ...editingDraft, subject: e.target.value })
                      }
                      className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded font-medium"
                    />
                  ) : (
                    <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded font-medium text-slate-800">
                      {selectedDraft.subject}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-slate-500 font-semibold mb-1">
                    Evidence-Grounded Body
                  </label>
                  {editingDraft ? (
                    <textarea
                      rows={8}
                      value={editingDraft.body}
                      onChange={(e) =>
                        setEditingDraft({ ...editingDraft, body: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded font-mono text-[11px]"
                    />
                  ) : (
                    <pre className="p-3.5 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] whitespace-pre-wrap leading-relaxed text-slate-800">
                      {selectedDraft.body}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-slate-400 text-xs">
              Select a draft from the queue to review or approve.
            </div>
          )}
        </div>
      </div>

      {/* HitL Feedback & Calibration Module */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <UserCheck className="w-4 h-4 text-orange-600" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Human-in-the-Loop (HitL) Scoring Calibration Feedback
          </h2>
        </div>
        <p className="text-xs text-slate-500">
          Provide qualitative accuracy feedback on model qualification decisions. Feedback records are stored and incorporated into continuous model training cycles.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs pt-1">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Target Lead Identifier
            </label>
            <input
              type="text"
              value={feedbackLeadId}
              onChange={(e) => setFeedbackLeadId(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded font-mono"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Qualification Accuracy
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFeedbackAccurate(true)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded border text-xs font-semibold ${
                  feedbackAccurate
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                    : 'bg-white text-slate-600 border-slate-200'
                }`}
              >
                <ThumbsUp className="w-3.5 h-3.5 text-emerald-600" />
                <span>Accurate</span>
              </button>
              <button
                type="button"
                onClick={() => setFeedbackAccurate(false)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded border text-xs font-semibold ${
                  !feedbackAccurate
                    ? 'bg-rose-50 text-rose-700 border-rose-300'
                    : 'bg-white text-slate-600 border-slate-200'
                }`}
              >
                <ThumbsDown className="w-3.5 h-3.5 text-rose-600" />
                <span>Inaccurate</span>
              </button>
            </div>
          </div>

          <div className="md:col-span-2">
            <label className="block font-semibold text-slate-700 mb-1">
              Qualitative Feedback Notes
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={feedbackNotes}
                onChange={(e) => setFeedbackNotes(e.target.value)}
                placeholder="Notes for model calibration..."
                className="flex-1 px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded"
              />
              <button
                onClick={handleSubmitFeedback}
                className="px-4 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800"
              >
                {feedbackSaved ? 'Recorded' : 'Submit Feedback'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
