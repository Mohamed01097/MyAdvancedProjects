# -*- coding: utf-8 -*-

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _xml_value(node, *names):
    for name in names:
        value = node.get(name)
        if value:
            return value.strip()
    return False


class DynamicViewElementMixin(models.AbstractModel):
    _name = 'dynamic.view.element.mixin'
    _description = 'Dynamic View Element Scanner'

    @api.model
    def _parse_form_arch(self, arch):
        if not arch:
            return False
        parser = etree.XMLParser(recover=True, remove_comments=True)
        return etree.fromstring(arch.encode('utf-8'), parser=parser)

    @api.model
    def _get_model_form_views(self, model):
        return self.env['ir.ui.view'].sudo().search([
            ('active', '=', True),
            ('model', '=', model.model),
            ('type', '=', 'form'),
        ], order='priority, id')

    @api.model
    def _get_combined_view_arch(self, view):
        try:
            return view.get_combined_arch()
        except Exception:
            return view.arch or ''

    @api.model
    def _collect_form_view_elements(self, model):
        buttons = {}
        tabs = {}
        for view in self._get_model_form_views(model):
            root = self._parse_form_arch(self._get_combined_view_arch(view))
            if root is False:
                continue

            for node in root.xpath('.//button[@name]'):
                technical_name = _xml_value(node, 'name')
                if not technical_name:
                    continue
                buttons.setdefault(
                    technical_name,
                    _xml_value(node, 'string', 'title', 'aria-label') or technical_name,
                )

            for node in root.xpath('.//notebook/page[@name]'):
                technical_name = _xml_value(node, 'name')
                if not technical_name:
                    continue
                tabs.setdefault(
                    technical_name,
                    _xml_value(node, 'string', 'title') or technical_name,
                )

        return buttons, tabs


class DynamicViewButton(models.Model):
    _name = 'dynamic.view.button'
    _description = 'Discovered View Button'
    _rec_name = 'name'
    _order = 'model_id, technical_name'

    name = fields.Char(compute='_compute_name', store=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    technical_name = fields.Char(required=True)
    display_label = fields.Char()

    _sql_constraints = [
        (
            'dynamic_view_button_model_technical_unique',
            'unique(model_id, technical_name)',
            'A discovered button must be unique per model.',
        ),
    ]

    @api.depends('model_id', 'technical_name', 'display_label')
    def _compute_name(self):
        for button in self:
            label = button.display_label or button.technical_name or ''
            technical_name = button.technical_name or ''
            button.name = label if label == technical_name else '%s (%s)' % (label, technical_name)

    @api.model
    def _upsert_for_model(self, model, values_by_name):
        created = 0
        updated = 0
        for technical_name, display_label in values_by_name.items():
            record = self.search([
                ('model_id', '=', model.id),
                ('technical_name', '=', technical_name),
            ], limit=1)
            values = {
                'model_id': model.id,
                'technical_name': technical_name,
                'display_label': display_label or technical_name,
            }
            if record:
                if record.display_label != values['display_label']:
                    record.write({'display_label': values['display_label']})
                    updated += 1
                continue
            self.create(values)
            created += 1
        return created, updated


class DynamicViewTab(models.Model):
    _name = 'dynamic.view.tab'
    _description = 'Discovered View Notebook Tab'
    _rec_name = 'name'
    _order = 'model_id, technical_name'

    name = fields.Char(compute='_compute_name', store=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    technical_name = fields.Char(required=True)
    display_label = fields.Char()

    _sql_constraints = [
        (
            'dynamic_view_tab_model_technical_unique',
            'unique(model_id, technical_name)',
            'A discovered notebook tab must be unique per model.',
        ),
    ]

    @api.depends('model_id', 'technical_name', 'display_label')
    def _compute_name(self):
        for tab in self:
            label = tab.display_label or tab.technical_name or ''
            technical_name = tab.technical_name or ''
            tab.name = label if label == technical_name else '%s (%s)' % (label, technical_name)

    @api.model
    def _upsert_for_model(self, model, values_by_name):
        created = 0
        updated = 0
        for technical_name, display_label in values_by_name.items():
            record = self.search([
                ('model_id', '=', model.id),
                ('technical_name', '=', technical_name),
            ], limit=1)
            values = {
                'model_id': model.id,
                'technical_name': technical_name,
                'display_label': display_label or technical_name,
            }
            if record:
                if record.display_label != values['display_label']:
                    record.write({'display_label': values['display_label']})
                    updated += 1
                continue
            self.create(values)
            created += 1
        return created, updated


class DynamicRestrictionButton(models.Model):
    _name = 'dynamic.restriction.button'
    _description = 'Dynamic Button Restriction'
    _order = 'button_name, id'

    name = fields.Char(compute='_compute_name', store=True)
    active = fields.Boolean(default=True)
    restriction_id = fields.Many2one('user.restrict', ondelete='cascade')
    model_id = fields.Many2one(
        'ir.model',
        string='Deprecated Model Scope',
        readonly=True,
        ondelete='cascade',
        help='Deprecated. Button restrictions now inherit models from the main restriction.',
    )
    button_element_id = fields.Many2one(
        'dynamic.view.button',
        string='Button',
        ondelete='restrict',
    )
    button_name = fields.Char()
    button_label = fields.Char()
    user_ids = fields.Many2many(
        'res.users',
        string='Deprecated Users',
        readonly=True,
        help='Deprecated. Button restrictions now inherit users from the main restriction.',
    )
    group_ids = fields.Many2many(
        'res.groups',
        string='Deprecated Groups',
        readonly=True,
        help='Deprecated. Button restrictions now inherit groups from the main restriction.',
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Deprecated Companies',
        readonly=True,
        help='Deprecated. Button restrictions now inherit companies from the main restriction.',
    )
    description = fields.Text()

    @api.depends('model_id', 'restriction_id.model_ids', 'button_name', 'button_label')
    def _compute_name(self):
        for rule in self:
            model_name = rule.model_id.model or rule.model_id.name or ''
            if not model_name and rule.restriction_id:
                model_name = ', '.join(rule.restriction_id.model_ids.mapped('model'))
            label = rule.button_label or rule.button_name or ''
            rule.name = ' / '.join(part for part in (model_name, label) if part)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        for rule in self:
            if rule.button_element_id and rule.button_element_id.model_id != rule.model_id:
                rule.button_element_id = False
                rule.button_name = False
                rule.button_label = False

    @api.onchange('button_element_id')
    def _onchange_button_element_id(self):
        for rule in self:
            rule._apply_button_element_values()

    def _apply_button_element_values(self):
        for rule in self:
            if not rule.button_element_id:
                continue
            rule.model_id = rule.model_id or rule.button_element_id.model_id
            rule.button_name = rule.button_element_id.technical_name
            rule.button_label = rule.button_element_id.display_label

    @api.model
    def _prepare_element_values(self, vals):
        element_id = vals.get('button_element_id')
        if not element_id:
            return vals
        element = self.env['dynamic.view.button'].browse(element_id).exists()
        if element:
            vals = dict(vals)
            vals.setdefault('model_id', element.model_id.id)
            vals['button_name'] = element.technical_name
            vals['button_label'] = element.display_label
        return vals

    @api.constrains('button_element_id', 'button_name')
    def _check_button_identifier(self):
        for rule in self:
            if not rule.button_element_id and not (rule.button_name or '').strip():
                raise UserError(_('Select a button or enter a button technical name.'))

    def _clear_dynamic_view_restriction_cache(self):
        self.env['user.restrict']._clear_dynamic_restriction_cache()

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._prepare_element_values(vals) for vals in vals_list]
        rules = super().create(vals_list)
        rules.mapped('restriction_id')._check_view_element_model_scope()
        rules._clear_dynamic_view_restriction_cache()
        return rules

    def write(self, vals):
        vals = self._prepare_element_values(vals)
        result = super().write(vals)
        self.mapped('restriction_id')._check_view_element_model_scope()
        self._clear_dynamic_view_restriction_cache()
        return result

    def unlink(self):
        self._clear_dynamic_view_restriction_cache()
        return super().unlink()


class DynamicRestrictionTab(models.Model):
    _name = 'dynamic.restriction.tab'
    _description = 'Dynamic Notebook Tab Restriction'
    _order = 'tab_name, id'

    name = fields.Char(compute='_compute_name', store=True)
    active = fields.Boolean(default=True)
    restriction_id = fields.Many2one('user.restrict', ondelete='cascade')
    model_id = fields.Many2one(
        'ir.model',
        string='Deprecated Model Scope',
        readonly=True,
        ondelete='cascade',
        help='Deprecated. Tab restrictions now inherit models from the main restriction.',
    )
    tab_element_id = fields.Many2one(
        'dynamic.view.tab',
        string='Tab',
        ondelete='restrict',
    )
    tab_name = fields.Char()
    tab_label = fields.Char()
    user_ids = fields.Many2many(
        'res.users',
        string='Deprecated Users',
        readonly=True,
        help='Deprecated. Tab restrictions now inherit users from the main restriction.',
    )
    group_ids = fields.Many2many(
        'res.groups',
        string='Deprecated Groups',
        readonly=True,
        help='Deprecated. Tab restrictions now inherit groups from the main restriction.',
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Deprecated Companies',
        readonly=True,
        help='Deprecated. Tab restrictions now inherit companies from the main restriction.',
    )
    description = fields.Text()

    @api.depends('model_id', 'restriction_id.model_ids', 'tab_name', 'tab_label')
    def _compute_name(self):
        for rule in self:
            model_name = rule.model_id.model or rule.model_id.name or ''
            if not model_name and rule.restriction_id:
                model_name = ', '.join(rule.restriction_id.model_ids.mapped('model'))
            label = rule.tab_label or rule.tab_name or ''
            rule.name = ' / '.join(part for part in (model_name, label) if part)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        for rule in self:
            if rule.tab_element_id and rule.tab_element_id.model_id != rule.model_id:
                rule.tab_element_id = False
                rule.tab_name = False
                rule.tab_label = False

    @api.onchange('tab_element_id')
    def _onchange_tab_element_id(self):
        for rule in self:
            rule._apply_tab_element_values()

    def _apply_tab_element_values(self):
        for rule in self:
            if not rule.tab_element_id:
                continue
            rule.model_id = rule.model_id or rule.tab_element_id.model_id
            rule.tab_name = rule.tab_element_id.technical_name
            rule.tab_label = rule.tab_element_id.display_label

    @api.model
    def _prepare_element_values(self, vals):
        element_id = vals.get('tab_element_id')
        if not element_id:
            return vals
        element = self.env['dynamic.view.tab'].browse(element_id).exists()
        if element:
            vals = dict(vals)
            vals.setdefault('model_id', element.model_id.id)
            vals['tab_name'] = element.technical_name
            vals['tab_label'] = element.display_label
        return vals

    @api.constrains('tab_element_id', 'tab_name')
    def _check_tab_identifier(self):
        for rule in self:
            if not rule.tab_element_id and not (rule.tab_name or '').strip():
                raise UserError(_('Select a tab or enter a tab technical name.'))

    def _clear_dynamic_view_restriction_cache(self):
        self.env['user.restrict']._clear_dynamic_restriction_cache()

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._prepare_element_values(vals) for vals in vals_list]
        rules = super().create(vals_list)
        rules.mapped('restriction_id')._check_view_element_model_scope()
        rules._clear_dynamic_view_restriction_cache()
        return rules

    def write(self, vals):
        vals = self._prepare_element_values(vals)
        result = super().write(vals)
        self.mapped('restriction_id')._check_view_element_model_scope()
        self._clear_dynamic_view_restriction_cache()
        return result

    def unlink(self):
        self._clear_dynamic_view_restriction_cache()
        return super().unlink()
