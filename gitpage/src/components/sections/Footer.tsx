import { repoUrl } from "../../config/site";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-white/10 bg-[#06081f] py-12">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-4 md:flex-row md:px-8">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-mint/30 bg-mint/10 text-sm font-bold text-mint">
            ASM
          </span>
          <div>
            <p className="font-semibold text-mist">App Suite Modeling</p>
            <p className="text-sm text-steel">Threat modeling for modern software delivery</p>
          </div>
        </div>
        <nav className="flex flex-wrap justify-center gap-6 text-sm text-steel" aria-label="Footer">
          <a href="#about" className="hover:text-mist">
            About
          </a>
          <a href="#features" className="hover:text-mist">
            Capabilities
          </a>
          <a href={repoUrl} className="hover:text-mist">
            GitHub
          </a>
        </nav>
        <p className="text-center text-xs text-slate md:text-right">
          © {year} App Suite Modeling contributors. Open source.
        </p>
      </div>
    </footer>
  );
}
