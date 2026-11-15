<?php

namespace Tests\Unit\AutoFix;

use Modules\AutoFix\Support\FixPolicy;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

final class FixPolicyTest extends TestCase
{
    #[Test]
    public function text_too_close_to_a_source_can_be_rewritten_by_auto_fix(): void
    {
        $this->assertTrue(FixPolicy::eligible(['type' => 'too_close_to_source', 'auto_fixable' => true]));
        $this->assertFalse(FixPolicy::eligible(['type' => 'contradiction', 'auto_fixable' => true]));
    }

    #[Test]
    public function an_unverified_number_can_be_corrected_by_auto_fix(): void
    {
        $this->assertTrue(FixPolicy::eligible(['type' => 'unverified_number', 'auto_fixable' => true]));
    }
}
