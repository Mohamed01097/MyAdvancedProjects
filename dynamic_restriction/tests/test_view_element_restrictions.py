import unittest

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestViewElementRestrictions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_model = cls.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        cls.sale_group = cls.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        if not cls.sale_model or not cls.sale_group:
            raise unittest.SkipTest('sale.order and Sales/User group are required for these tests.')

        cls.partner_model = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Restriction Test Company B'})
        cls.base_user_group = cls.env.ref('base.group_user')
        cls.normal_user = cls._create_user('restriction_normal_user')
        cls.group_user = cls._create_user('restriction_group_user', cls.sale_group)
        cls.admin_user = cls.env.ref('base.user_admin')

    @classmethod
    def _create_user(cls, login, extra_group=False):
        groups = cls.base_user_group
        if extra_group:
            groups |= extra_group
        return cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': login.replace('_', ' ').title(),
            'login': login,
            'email': '%s@example.com' % login,
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])],
            'group_ids': [(6, 0, groups.ids)],
        })

    def _create_restriction(self, users=False, groups=False, companies=False, button=True, tab=True):
        values = {
            'name': 'Sale Order View Element Restriction',
            'model_ids': [(6, 0, [self.sale_model.id])],
        }
        if users:
            values['user_ids'] = [(6, 0, users.ids)]
        if groups:
            values['group_ids'] = [(6, 0, groups.ids)]
        if companies:
            values['company_ids'] = [(6, 0, companies.ids)]
        restriction = self.env['user.restrict'].create(values)
        if button:
            self.env['dynamic.restriction.button'].create({
                'restriction_id': restriction.id,
                'button_name': 'action_confirm',
                'button_label': 'Confirm',
            })
        if tab:
            self.env['dynamic.restriction.tab'].create({
                'restriction_id': restriction.id,
                'tab_name': 'other_information',
                'tab_label': 'Other Information',
            })
        return restriction

    def _get_view_restrictions(self, user, company=False):
        return self.env['user.restrict'].with_user(user).with_company(
            company or self.company_a
        ).get_view_ui_restrictions('sale.order')

    def test_button_rule_uses_parent_user_scope(self):
        self._create_restriction(users=self.normal_user, button=True, tab=False)

        result = self._get_view_restrictions(self.normal_user)

        self.assertIn({'name': 'action_confirm', 'label': 'Confirm'}, result['buttons'])

    def test_tab_rule_returns_object_and_uses_parent_user_scope(self):
        self._create_restriction(users=self.normal_user, button=False, tab=True)

        result = self._get_view_restrictions(self.normal_user)

        self.assertIn(
            {'name': 'other_information', 'label': 'Other Information'},
            result['tabs'],
        )

    def test_button_and_tab_rules_use_parent_group_scope(self):
        self._create_restriction(groups=self.sale_group, button=True, tab=True)

        result = self._get_view_restrictions(self.group_user)

        self.assertIn({'name': 'action_confirm', 'label': 'Confirm'}, result['buttons'])
        self.assertIn(
            {'name': 'other_information', 'label': 'Other Information'},
            result['tabs'],
        )

    def test_button_and_tab_rules_use_parent_company_scope(self):
        self._create_restriction(
            users=self.normal_user,
            companies=self.company_a,
            button=True,
            tab=True,
        )

        company_a_result = self._get_view_restrictions(self.normal_user, self.company_a)
        company_b_result = self._get_view_restrictions(self.normal_user, self.company_b)

        self.assertIn({'name': 'action_confirm', 'label': 'Confirm'}, company_a_result['buttons'])
        self.assertIn(
            {'name': 'other_information', 'label': 'Other Information'},
            company_a_result['tabs'],
        )
        self.assertEqual(company_b_result, {'buttons': [], 'tabs': []})

    def test_admin_bypass_sees_all_view_elements(self):
        self._create_restriction(users=self.admin_user, button=True, tab=True)

        result = self._get_view_restrictions(self.admin_user)

        self.assertEqual(result, {'buttons': [], 'tabs': []})

    def test_button_tab_restrictions_require_one_parent_model(self):
        restriction = self.env['user.restrict'].create({
            'name': 'Multi Model View Element Restriction',
            'model_ids': [(6, 0, [self.sale_model.id, self.partner_model.id])],
            'user_ids': [(6, 0, self.normal_user.ids)],
        })

        with self.assertRaisesRegex(
            UserError,
            'Button and Tab restrictions require exactly one model on the main restriction.',
        ):
            self.env['dynamic.restriction.button'].create({
                'restriction_id': restriction.id,
                'button_name': 'action_confirm',
                'button_label': 'Confirm',
            })
