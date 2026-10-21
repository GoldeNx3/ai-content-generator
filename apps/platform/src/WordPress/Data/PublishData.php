<?php

namespace Modules\WordPress\Data;

use Carbon\CarbonImmutable;
use Illuminate\Validation\Validator;
use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Regex;
use Spatie\LaravelData\Data;

final class PublishData extends Data
{
    public function __construct(
        #[In(['draft', 'future', 'publish'])]
        public string $status = 'draft',
        public ?string $scheduled_at = null,
        #[Regex('/^[a-f0-9]{64}$/')]
        public ?string $expected_wp_hash = null,
    ) {}

    public static function rules(): array
    {
        return ['scheduled_at' => ['nullable', 'date', 'required_if:status,future', 'prohibited_unless:status,future']];
    }

    public static function withValidator(Validator $validator): void
    {
        $validator->after(function (Validator $validator): void {
            $data = $validator->getData();
            if (($data['status'] ?? null) !== 'future' || empty($data['scheduled_at'])) {
                return;
            }
            if (! preg_match('/(Z|[+-]\d{2}:?\d{2})$/', (string) $data['scheduled_at'])) {
                $validator->errors()->add('scheduled_at', 'Schedule requires a datetime with timezone.');
            } elseif (CarbonImmutable::parse($data['scheduled_at'])->lessThanOrEqualTo(CarbonImmutable::now())) {
                $validator->errors()->add('scheduled_at', 'Scheduled date must be in the future.');
            }
        });
    }

    public function options(): array
    {
        return [
            'status' => $this->status,
            'scheduled_at' => $this->scheduled_at === null ? null : CarbonImmutable::parse($this->scheduled_at)->utc()->toIso8601String(),
            'expected_wp_hash' => $this->expected_wp_hash,
        ];
    }
}
