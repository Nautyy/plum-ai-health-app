import Image from "next/image";

type Props = {
  className?: string;
};

export default function PlumLogo({ className = "h-6 w-auto" }: Props) {
  return (
    <Image
      src="/plum-logo.png"
      alt="Plum"
      width={80}
      height={28}
      priority
      className={className}
    />
  );
}
