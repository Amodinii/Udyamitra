import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import useAutoScroll from '../../hooks/useAutoScroll';
import Spinner from '../chat/Spinner';
import DataTable from './DataTable';

function ChatMessages({ messages, isLoading }) {
    const scrollContentRef = useAutoScroll(isLoading);

    return (
        <div
            ref={scrollContentRef}
            className="grow space-y-4 px-2 overflow-y-auto"
        >
            {messages.map(({ role, content, loading, error }, idx) => {
                const isUser = role === 'user';
                const rowClass = isUser ? 'flex w-full justify-end' : 'flex w-full justify-start';
                const bubbleBase = 'rounded-xl px-4 py-3 shadow-sm max-w-[80%] whitespace-pre-wrap text-left'; 
                const bubbleClass = isUser
                    ? `${bubbleBase} bg-[#DEDEDE]`
                    : `${bubbleBase} bg-[#FFFFFF] border border-gray-200`;
                const innerLayout = isUser ? 'flex items-start gap-3 flex-row-reverse' : 'flex items-start gap-3';

                // --- UPDATED result extraction logic ---
                let result = null;
                if (content && typeof content === 'object') {
                    const firstKey = Object.keys(content)[0];
                    const toolOutput = content[firstKey];

                    if (toolOutput) {
                        // Check for raw_output.data_table first
                        if (toolOutput.raw_output?.data_table) {
                            result = {
                                ...toolOutput.raw_output,
                                insight_summary: toolOutput.raw_output.insight_summary || '',
                                detailed_explanation: toolOutput.raw_output.detailed_explanation || '',
                                actionable_steps: toolOutput.raw_output.actionable_steps || [],
                                data_table: toolOutput.raw_output.data_table
                            };
                        } 
                        // Fallback: try parsing output_text if needed
                        else if (toolOutput.output_text) {
                            try {
                                const parsed = JSON.parse(toolOutput.output_text);
                                if (parsed.data_table) result = parsed;
                            } catch {
                                // fallback: no-op
                            }
                        }
                    }
                }

                const hasTable = !!result?.data_table;
                // --- END extraction logic ---

                return (
                    <div key={idx} className={rowClass}>
                        <div className={innerLayout}>
                            <div className={bubbleClass}>
                                <div className="markdown-container">
                                    {loading && !content ? (
                                        <Spinner />
                                    ) : !isUser ? (
                                        // Assistant message
                                        hasTable ? (
                                            <div>
                                                {result.insight_summary && (
                                                    <p className="font-bold mb-2">{result.insight_summary}</p>
                                                )}
                                                {result.detailed_explanation && (
                                                    <p className="text-sm mb-2">{result.detailed_explanation}</p>
                                                )}

                                                {/* Render the table */}
                                                <DataTable data={result.data_table} />

                                                {result.actionable_steps && result.actionable_steps.length > 0 && (
                                                    <div className="mt-4">
                                                        <h4 className="font-semibold text-sm mb-1">Your Next Steps:</h4>
                                                        <ul className="list-disc list-inside text-sm space-y-1">
                                                            {result.actionable_steps.map((step, i) => (
                                                                <li key={i}>{step.replace(/^\d+\.\s*/, '')}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            // Default Markdown fallback (non-table responses)
                                            <Markdown
                                                remarkPlugins={[remarkGfm]}
                                                components={{
                                                    p: ({ children }) => (
                                                        <p className="whitespace-pre-line">{children}</p>
                                                    ),
                                                    table: ({ children }) => (
                                                        <div className="overflow-x-auto my-4">
                                                            <table className="min-w-full border border-gray-200 text-sm text-left">
                                                                {children}
                                                            </table>
                                                        </div>
                                                    ),
                                                    thead: ({ children }) => (
                                                        <thead className="bg-gray-50 border-b">{children}</thead>
                                                    ),
                                                    th: ({ children }) => (
                                                        <th className="px-4 py-2 border-b font-semibold text-gray-700 bg-gray-100">
                                                            {children}
                                                        </th>
                                                    ),
                                                    td: ({ children }) => (
                                                        <td className="px-4 py-2 border-b text-gray-800">
                                                            {children}
                                                        </td>
                                                    ),
                                                }}
                                            >
                                                {typeof content === 'string'
                                                    ? content
                                                    : Object.entries(content || {})
                                                        .map(([tool, res]) =>
                                                            `### Tool used for the query: ${tool}\n\n${
                                                                res.output_text || JSON.stringify(res, null, 2)
                                                            }`
                                                        )
                                                        .join('\n\n')}
                                            </Markdown>
                                        )
                                    ) : (
                                        // 🧍 User message
                                        <div className="whitespace-pre-line">
                                            {typeof content === 'string'
                                                ? content
                                                : JSON.stringify(content, null, 2)}
                                        </div>
                                    )}
                                </div>

                                {error && (
                                    <div className="flex items-center gap-1 text-sm text-red-600 mt-2">
                                        <span>Error generating the response</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default ChatMessages;
