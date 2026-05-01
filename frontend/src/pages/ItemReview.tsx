import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getItems, updateItemBrand, patchItemMetadata, addItemPhotos, getItemPhotos } from "../api";
import { ColorPickerPair } from "../components/ColorPickerPair";
import { MetadataField, type MetadataFieldStatus } from "../components/MetadataField";
import { FilePickerButton } from "../components/FilePickerButton";
import { useToast } from "../components/ToastProvider";

interface Item {
  id: number;
  brand: string;
  description: string;
  condition_score: number | null;
  status: string;
  primary_color?: string;
  secondary_colors?: string[];
  style?: string;
  material?: string;
  width_in?: number | null;
  height_in?: number | null;
  depth_in?: number | null;
  serial_number?: string;
  asking_price?: number | null;
}

interface ItemPhoto {
  id: number;
  thumbnail_key: string | null;
  storage_key: string;
  is_hero: boolean;
  sort_order: number;
}

function photoThumbUrl(photo: ItemPhoto): string {
  const key = photo.thumbnail_key || photo.storage_key;
  return `/photos/${encodeURIComponent(key)}/thumb`;
}

type SaveStatus = Map<string, MetadataFieldStatus>;

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    keeper: "bg-forest text-white",
    seller: "bg-terracotta text-white",
    unranked: "bg-transparent text-muted border border-dusty-rose",
  };
  const cls = variants[status] ?? variants.unranked;
  return (
    <span className={`text-[10px] uppercase tracking-widest font-sans px-2.5 py-1 ${cls}`}>
      {status}
    </span>
  );
}

const STYLE_OPTIONS = ['tote', 'satchel', 'clutch', 'crossbody', 'hobo', 'backpack', 'shoulder', 'bucket', 'other'];
const MATERIAL_OPTIONS = ['leather', 'canvas', 'suede', 'fabric', 'straw', 'patent', 'exotic', 'other'];

function ItemCard({
  item,
  cid,
  onBrandSave,
}: {
  item: Item;
  cid: number;
  onBrandSave: (itemId: number, brand: string) => void;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [editBrand, setEditBrand] = useState(item.brand);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>(new Map());

  // Metadata form state
  const [primaryColor, setPrimaryColor] = useState(item.primary_color ?? '');
  const [secondaryColors, setSecondaryColors] = useState<string[]>(item.secondary_colors ?? []);
  const [style, setStyle] = useState(item.style ?? '');
  const [material, setMaterial] = useState(item.material ?? '');
  const [widthIn, setWidthIn] = useState(item.width_in != null ? String(item.width_in) : '');
  const [heightIn, setHeightIn] = useState(item.height_in != null ? String(item.height_in) : '');
  const [depthIn, setDepthIn] = useState(item.depth_in != null ? String(item.depth_in) : '');
  const [serialNumber, setSerialNumber] = useState(item.serial_number ?? '');
  const [askingPrice, setAskingPrice] = useState(item.asking_price != null ? String(item.asking_price) : '');

  // Photos
  const [photos, setPhotos] = useState<ItemPhoto[]>([]);
  const [photosLoaded, setPhotosLoaded] = useState(false);

  useEffect(() => {
    getItemPhotos(cid, item.id)
      .then((data: ItemPhoto[]) => { setPhotos(data); setPhotosLoaded(true); })
      .catch(() => setPhotosLoaded(true));
  }, [cid, item.id]);

  const setFieldStatus = (field: string, status: MetadataFieldStatus) => {
    setSaveStatus((prev) => new Map(prev).set(field, status));
  };

  const saveBrand = async () => {
    await updateItemBrand(cid, item.id, editBrand);
    onBrandSave(item.id, editBrand);
    setEditing(false);
  };

  const saveMetadata = async () => {
    const fields: Record<string, unknown> = {};
    if (primaryColor) fields.primary_color = primaryColor;
    fields.secondary_colors = secondaryColors;
    if (style) fields.style = style;
    if (material) fields.material = material;
    if (widthIn) fields.width_in = parseFloat(widthIn);
    if (heightIn) fields.height_in = parseFloat(heightIn);
    if (depthIn) fields.depth_in = parseFloat(depthIn);
    if (serialNumber) fields.serial_number = serialNumber;
    if (askingPrice) fields.asking_price = parseFloat(askingPrice);

    setFieldStatus('metadata', 'saving');
    try {
      await patchItemMetadata(cid, item.id, fields);
      setFieldStatus('metadata', 'saved');
      setTimeout(() => setFieldStatus('metadata', 'idle'), 1500);
    } catch {
      setFieldStatus('metadata', 'error');
      toast.error('Failed to save metadata.');
    }
  };

  const handleColorChange = ({ primary, secondary }: { primary: string; secondary: string[] }) => {
    setPrimaryColor(primary);
    setSecondaryColors(secondary);
  };

  const handleAddPhotos = async (files: File[]) => {
    try {
      const results = await addItemPhotos(cid, item.id, files);
      // Refetch photos to get fresh list
      const data = await getItemPhotos(cid, item.id) as ItemPhoto[];
      setPhotos(data);
      void results; // results are ItemPhotoRead objects but we refetch anyway
    } catch {
      toast.error('Failed to upload photos to this item.');
    }
  };

  const metadataStatus = saveStatus.get('metadata') ?? 'idle';

  return (
    <div data-testid="item-card" className="bg-white border border-cream p-5">
      {/* Brand + Status row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                value={editBrand}
                onChange={(e) => setEditBrand(e.target.value)}
                className="font-serif text-base border-b border-terracotta bg-transparent outline-none text-near-black py-0.5 flex-1 min-w-0"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && saveBrand()}
              />
              <button
                onClick={saveBrand}
                className="text-[10px] uppercase tracking-widest font-sans bg-terracotta text-white px-3 py-1.5 hover:bg-terracotta/80 transition-colors cursor-pointer shrink-0"
              >
                Save
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setEditing(true); setEditBrand(item.brand); }}
              className="font-serif text-base text-near-black cursor-pointer hover:text-terracotta transition-colors bg-transparent border-none p-0 text-left"
              title="Click to edit brand"
            >
              {item.brand === "unknown" ? "Unknown brand" : item.brand}
            </button>
          )}
        </div>
        <StatusBadge status={item.status} />
      </div>

      {item.condition_score !== null && (
        <div className="mt-3">
          <div className="h-1 bg-dusty-rose/30 w-full overflow-hidden">
            <div
              className="h-full bg-saffron"
              style={{ width: `${Math.round((item.condition_score ?? 0) * 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-muted font-sans mt-1 uppercase tracking-widest">
            {Math.round((item.condition_score ?? 0) * 100)}% condition
          </p>
        </div>
      )}

      {/* PHOTOS section */}
      <div className="mt-5">
        <p className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-3">Photos</p>
        <div className="flex flex-wrap gap-1.5 items-center">
          {photosLoaded && photos.map((photo) => (
            <div
              key={photo.id}
              className={`relative w-16 h-16 overflow-hidden ${photo.is_hero ? 'border-b-2 border-saffron' : ''}`}
            >
              <img
                src={photoThumbUrl(photo)}
                alt="Item photo"
                loading="lazy"
                className="w-full h-full object-cover"
              />
            </div>
          ))}
          {/* Add photos button */}
          <FilePickerButton
            label="+ Add photos"
            multiple
            onFiles={handleAddPhotos}
            className="w-16 h-16 border border-dashed border-cobalt text-cobalt bg-transparent hover:bg-cobalt/5 text-xs"
          />
        </div>
      </div>

      {/* DETAILS section */}
      <div className="mt-5">
        <p className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-4">Details</p>

        <div className="flex flex-col gap-4">
          <ColorPickerPair
            primary={primaryColor}
            secondary={secondaryColors}
            onChange={handleColorChange}
          />

          <MetadataField label="Style" status="idle">
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm focus:border-terracotta outline-none w-full"
            >
              <option value="">— select —</option>
              {STYLE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </MetadataField>

          <MetadataField label="Material" status="idle">
            <select
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm focus:border-terracotta outline-none w-full"
            >
              <option value="">— select —</option>
              {MATERIAL_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </MetadataField>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-[0.25em] text-muted font-sans">
              Dimensions (in)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'W', value: widthIn, onChange: setWidthIn },
                { label: 'H', value: heightIn, onChange: setHeightIn },
                { label: 'D', value: depthIn, onChange: setDepthIn },
              ].map(({ label, value, onChange }) => (
                <div key={label} className="flex items-center gap-1">
                  <span className="text-[10px] text-muted font-sans">{label}</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="bg-cream border-b border-muted/40 px-0 py-1 font-sans text-sm outline-none focus:border-terracotta w-full"
                  />
                </div>
              ))}
            </div>
          </div>

          <MetadataField label="Serial Number" status="idle">
            <input
              type="text"
              value={serialNumber}
              onChange={(e) => setSerialNumber(e.target.value)}
              className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm outline-none focus:border-terracotta w-full"
            />
          </MetadataField>

          <MetadataField label="Asking Price" status="idle">
            <div className="flex items-center gap-1">
              <span className="text-muted font-sans text-sm">$</span>
              <input
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                pattern="[0-9]*"
                value={askingPrice}
                onChange={(e) => setAskingPrice(e.target.value)}
                className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm outline-none focus:border-terracotta flex-1"
              />
            </div>
          </MetadataField>

          {/* Save button + status */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={saveMetadata}
              onKeyDown={(e) => e.key === 'Enter' && saveMetadata()}
              disabled={metadataStatus === 'saving'}
              className="bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer disabled:opacity-50"
            >
              Save
            </button>
            {metadataStatus === 'saving' && (
              <span className="text-[10px] text-muted font-sans">Saving…</span>
            )}
            {metadataStatus === 'saved' && (
              <span className="text-[10px] text-forest font-sans">✓ Saved</span>
            )}
            {metadataStatus === 'error' && (
              <span className="text-[11px] text-terracotta font-sans">Failed to save</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ItemReview() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const cid = Number(collectionId);
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    getItems(cid).then(setItems).catch(() => {});
  }, [cid]);

  const handleBrandSave = (itemId: number, brand: string) => {
    setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, brand } : i)));
  };

  return (
    <div className="min-h-screen bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
          Operator
        </p>
        <h1 className="font-serif text-3xl text-near-black leading-tight">Item Review</h1>
      </header>

      <main className="px-6 py-8 max-w-2xl mx-auto">
        {items.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">No items in this collection.</p>
        ) : (
          <div className="grid gap-3">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} cid={cid} onBrandSave={handleBrandSave} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
