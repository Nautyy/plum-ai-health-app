type Props = {
  className?: string;
};

export default function AssistantAvatar({ className = "" }: Props) {
  return (
    <div
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-plum-brand text-[13px] font-bold leading-none text-white ${className}`}
      aria-hidden="true"
    >
      p
    </div>
  );
}
