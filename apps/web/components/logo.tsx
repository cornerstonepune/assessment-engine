import Image from "next/image";

// The Cornerstone mark (apps/web/public/brand/cornerstone-mark.svg): the one logo of the site, in the top bar, on the
// sign-in page and as the tab icon (app/icon.svg). A vector, so it is drawn as it is and never resized by the server.
export function Logo({ size = 28 }: { size?: number }) {
  return <Image src="/brand/cornerstone-mark.svg" alt="" width={size} height={size} unoptimized data-brand-mark priority />;
}
