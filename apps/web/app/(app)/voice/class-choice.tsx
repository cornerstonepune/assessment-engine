import Link from "@/components/link";
import type { MyVoice } from "@/lib/voice-types";
import { classWords } from "@/lib/voice-types";
import { W } from "@/lib/voice-words";

/** Her classes as buttons, when she has more than one and the address named none. */
export function ClassChoice({ my, href }: { my: MyVoice; href: (id: string) => string }) {
  return (
    <section className="grid gap-2" aria-label={W.record.whichClass}>
      <h2 className="text-[16px]">{W.record.whichClass}</h2>
      <div className="flex flex-wrap gap-2">
        {my.classes.map((c) => (
          <Link key={c.id} href={href(c.id)} className="btn secondary">
            {classWords(c)}
          </Link>
        ))}
      </div>
    </section>
  );
}
