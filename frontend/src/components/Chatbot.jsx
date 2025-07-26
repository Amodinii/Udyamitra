import { useState, useEffect } from 'react';
import { useImmer } from 'use-immer';
import api from '@/api';
import ChatMessages from '@/components/ChatMessages';
import ChatInput from '@/components/ChatInput';

function Chatbot() {
  const [messages, setMessages] = useImmer([]);
  const [newMessage, setNewMessage] = useState('');
  const [isPolling, setIsPolling] = useState(false);

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

    // Show user message and assistant placeholder
    setMessages(draft => [
      ...draft,
      { role: 'user', content: trimmedMessage },
      { role: 'assistant', content: 'Processing your query...', loading: true }
    ]);
    setNewMessage('');

    try {
      await api.startPipeline(trimmedMessage);
      setIsPolling(true);
    } catch (err) {
      console.error(err);
      setMessages(draft => {
        draft[draft.length - 1] = {
          role: 'assistant',
          content: 'Something went wrong while starting the pipeline.',
          loading: false
        };
      });
    }
  };

  // Poll status every 2s
  useEffect(() => {
    if (!isPolling) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getPipelineStatus();

        // If stage has changed or final output is ready, update message
        setMessages(draft => {
          const last = draft[draft.length - 1];

          if (status.stage === 'COMPLETED' && status.results) {
            draft[draft.length - 1] = {
              role: 'assistant',
              content: JSON.stringify(status.results, null, 2),
              loading: false
            };
            setIsPolling(false);
            clearInterval(interval);
          } else {
            // update progress message (you can make this smarter)
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
  }, [isPolling]);

  return (
    <div className='relative grow flex flex-col gap-6 pt-6'>
      {messages.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="font-urbanist text-4xl font-semibold text-white text-center px-4">
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