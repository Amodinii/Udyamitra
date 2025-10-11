import { useState, useEffect } from 'react';
import { useImmer } from 'use-immer';
import api from '../api'
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';

function Chatbot() {
    const [messages, setMessages] = useImmer([]);
    const [newMessage, setNewMessage] = useState('');
    const [isPolling, setIsPolling] = useState(false);
    const [conversationState, setConversationState] = useState(null);

    const isLoading = isPolling;

    const getTimeBasedGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning!';
        if (hour < 18) return 'Good afternoon!';
        return 'Good evening!';
    };

    const submitNewMessage = async () => {
        const trimmedMessage = newMessage.trim();
        if (!trimmedMessage || isPolling) return;

        console.log(`User Message in Chatbot.jsx: ${trimmedMessage}`);
        setMessages(draft => [
        ...draft,
        { role: 'user', content: trimmedMessage },
        { role: 'assistant', content: 'Processing your query...', loading: true }
        ]);
        setNewMessage('');

        try {
        let response;

        if (conversationState) {
            response = await api.continuePipeline(trimmedMessage, conversationState);
        } else {
            response = await api.startPipeline(trimmedMessage);
        }

        if (response.state) {
            setConversationState(response.state);
        }
        setIsPolling(true);
        } catch (err) {
        console.error(err);
        setMessages(draft => {
            draft[draft.length - 1] = {
            role: 'assistant',
            content: 'Something went wrong while processing your query.',
            loading: false
            };
        });
        }
    };

    useEffect(() => {
        if (!isPolling) return;

        const interval = setInterval(async () => {
        try {
            const status = await api.getPipelineStatus();
            console.log(`Status from /status: ${JSON.stringify(status)}`);

            if (status.state) {
                setConversationState(status.state);
            }

            setMessages(draft => {
                const last = draft[draft.length - 1];
                if (status.stage === 'COMPLETED' && status.results) {
                    console.log(`Results: ${JSON.stringify(status.results)}`);
                    
                    // --- THE ONLY MODIFICATION ---
                    // This passes the raw results object, allowing ChatMessages to decide how to render it.
                    draft[draft.length - 1] = {
                        role: 'assistant',
                        content: status.results,
                        loading: false
                    };
                    // --- END OF MODIFICATION ---

                    setIsPolling(false);
                    clearInterval(interval);
                } else {
                    last.content = `Current stage: ${status.stage}`;
                }
            });
        } catch (err) {
            console.error('Error polling pipeline:', err);
            setMessages(draft => {
            draft[draft.length - 1] = {
                role: 'assistant',
                content: 'Error checking pipeline status.',
                loading: false
            };
            });
            setIsPolling(false);
            clearInterval(interval);
        }
        }, 2000);

        return () => clearInterval(interval);
    }, [isPolling, setMessages]);

    return (
        <div className='relative grow flex flex-col gap-6 pt-6'>
        {messages.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
            <p className="font-urbanist text-4xl font-semibold text-[#272727] text-center px-4">
                Hello there, {getTimeBasedGreeting()}
            </p>
            </div>
        )}

        <ChatMessages messages={messages} isLoading={isLoading} />
        <ChatInput
            newMessage={newMessage}
            isLoading={isLoading}
            setNewMessage={setNewMessage}
            submitNewMessage={submitNewMessage}
        />
        </div>
    );
}

export default Chatbot;